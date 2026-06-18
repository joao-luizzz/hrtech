import logging
from django.core.management.base import BaseCommand
from core.neo4j_connection import run_query
from core.validators import normalize_skill_name

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Normaliza nomes de Habilidades existentes no Neo4j e mescla nós duplicados (por diferença de case/espaço).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas relata quais nós seriam mesclados ou renomeados, sem alterar o banco.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('Iniciando normalização de habilidades no Neo4j...'))
        if dry_run:
            self.stdout.write(self.style.NOTICE('MODO DRY-RUN: Nenhuma alteração real será feita.'))

        # 1. Obter todas as habilidades do Neo4j
        query_all = "MATCH (h:Habilidade) RETURN id(h) as node_id, h.nome as nome"
        resultados = run_query(query_all)
        
        if not resultados:
            self.stdout.write(self.style.SUCCESS('Nenhuma habilidade encontrada no Neo4j.'))
            return

        habilidades = [(r['node_id'], r['nome']) for r in resultados]
        self.stdout.write(f'Encontradas {len(habilidades)} habilidades para análise.')

        to_rename = []  # Apenas renomeia o nó (novo nome não existe)
        to_merge = []   # Nó antigo deve ser mesclado ao novo que já existe

        # Mapeia nomes existentes (normalizados ou não) para sabermos se o alvo já existe
        nomes_atuais = {h[1] for h in habilidades}

        for node_id, nome_original in habilidades:
            nome_normalizado = normalize_skill_name(nome_original)
            
            if not nome_normalizado:
                # Skill vazia ou totalmente inválida, deve ser apagada
                self.stdout.write(self.style.ERROR(f"Skill com nome inválido/vazio encontrada: '{nome_original}'"))
                continue

            if nome_original != nome_normalizado:
                if nome_normalizado in nomes_atuais:
                    to_merge.append((nome_original, nome_normalizado))
                else:
                    to_rename.append((nome_original, nome_normalizado))
                    # Adiciona o novo nome no controle para as próximas iterações saberem que ele vai existir
                    nomes_atuais.add(nome_normalizado)

        self.stdout.write(f'\nResumo das ações necessárias:')
        self.stdout.write(f'- {len(to_rename)} nós serão APENAS RENOMEADOS.')
        self.stdout.write(f'- {len(to_merge)} nós serão MESCLADOS (nó destino já existe).')

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n=== DRY RUN DETALHES ==='))
            for old, new in to_rename:
                self.stdout.write(f"RENAME: '{old}' -> '{new}'")
            for old, new in to_merge:
                self.stdout.write(f"MERGE:  '{old}' -> '{new}' (Transferindo relações e apagando o antigo)")
            self.stdout.write(self.style.SUCCESS('\nDry-run concluído.'))
            return

        # Executando RENAME
        renamed_count = 0
        for old_name, new_name in to_rename:
            query_rename = """
            MATCH (h:Habilidade {nome: $old_name})
            SET h.nome = $new_name
            """
            try:
                run_query(query_rename, {'old_name': old_name, 'new_name': new_name})
                renamed_count += 1
                self.stdout.write(f"Renomeado: '{old_name}' para '{new_name}'")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao renomear '{old_name}': {e}"))

        # Executando MERGE
        merged_count = 0
        for old_name, new_name in to_merge:
            query_merge = """
            MATCH (a:Habilidade {nome: $old_name})
            MATCH (b:Habilidade {nome: $new_name})

            // Transfere TEM_HABILIDADE (Candidato -> Habilidade)
            OPTIONAL MATCH (c:Candidato)-[r_tem:TEM_HABILIDADE]->(a)
            FOREACH (ignoreMe IN CASE WHEN r_tem IS NOT NULL THEN [1] ELSE [] END |
                MERGE (c)-[new_r:TEM_HABILIDADE]->(b)
                SET new_r = properties(r_tem)
                DELETE r_tem
            )

            WITH a, b
            // Transfere REQUER (Vaga -> Habilidade) - Legado, mas seguro manter
            OPTIONAL MATCH (v:Vaga)-[r_req:REQUER]->(a)
            FOREACH (ignoreMe IN CASE WHEN r_req IS NOT NULL THEN [1] ELSE [] END |
                MERGE (v)-[new_r2:REQUER]->(b)
                SET new_r2 = properties(r_req)
                DELETE r_req
            )

            WITH a, b
            // Transfere SIMILAR_A (Habilidade -> Outra)
            OPTIONAL MATCH (a)-[r_sim_out:SIMILAR_A]->(h_out)
            FOREACH (ignoreMe IN CASE WHEN r_sim_out IS NOT NULL THEN [1] ELSE [] END |
                MERGE (b)-[new_sim_out:SIMILAR_A]->(h_out)
                SET new_sim_out = properties(r_sim_out)
                DELETE r_sim_out
            )

            WITH a, b
            // Transfere SIMILAR_A (Outra -> Habilidade)
            OPTIONAL MATCH (h_in)-[r_sim_in:SIMILAR_A]->(a)
            FOREACH (ignoreMe IN CASE WHEN r_sim_in IS NOT NULL THEN [1] ELSE [] END |
                MERGE (h_in)-[new_sim_in:SIMILAR_A]->(b)
                SET new_sim_in = properties(r_sim_in)
                DELETE r_sim_in
            )

            // Finalmente, deleta o nó antigo duplicado
            DETACH DELETE a
            """
            try:
                run_query(query_merge, {'old_name': old_name, 'new_name': new_name})
                merged_count += 1
                self.stdout.write(f"Mesclado: '{old_name}' para '{new_name}' (relações transferidas)")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao mesclar '{old_name}' para '{new_name}': {e}"))

        self.stdout.write(self.style.SUCCESS(f'\nConcluído! Renomeados: {renamed_count}, Mesclados: {merged_count}.'))
