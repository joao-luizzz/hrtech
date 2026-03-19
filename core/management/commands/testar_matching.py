"""
HRTech - Comando de Management: testar_matching
================================================

Comando para testar o algoritmo de matching diretamente no terminal.

Uso:
    python manage.py testar_matching                    # Testa todas as vagas
    python manage.py testar_matching --vaga 1          # Testa vaga específica
    python manage.py testar_matching --limite 10       # Limita candidatos
    python manage.py testar_matching --sem-auditoria   # Não salva na AuditoriaMatch
    python manage.py testar_matching --verbose         # Mostra detalhes de cada camada

Output:
    Ranking colorido no terminal com:
    - Posição e score
    - Nome e senioridade do candidato
    - Breakdown das 3 camadas
    - Gap analysis resumido

Decisões:
---------
- Cores ANSI para melhor legibilidade (funciona no Linux/Mac/WSL)
- Fallback para sem cores se terminal não suportar
- Tabela formatada com padding para alinhamento
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
import sys

from core.models import Vaga
from core.matching import MatchingEngine, VERSAO_ALGORITMO, resultado_para_dict


# =============================================================================
# CORES ANSI PARA TERMINAL
# =============================================================================
class Colors:
    """Códigos ANSI para colorir output no terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

    @classmethod
    def disable(cls):
        """Desabilita cores (para terminais que não suportam)."""
        cls.HEADER = ''
        cls.BLUE = ''
        cls.CYAN = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.RED = ''
        cls.ENDC = ''
        cls.BOLD = ''
        cls.UNDERLINE = ''
        cls.DIM = ''


def score_color(score: float) -> str:
    """Retorna cor apropriada baseada no score."""
    if score >= 80:
        return Colors.GREEN
    elif score >= 60:
        return Colors.CYAN
    elif score >= 40:
        return Colors.YELLOW
    else:
        return Colors.RED


class Command(BaseCommand):
    """
    Testa o algoritmo de matching no terminal.

    Exibe ranking de candidatos para uma ou mais vagas,
    com visualização colorida e breakdown de scores.
    """
    help = 'Testa o algoritmo de matching e exibe ranking de candidatos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vaga',
            type=int,
            help='ID da vaga específica para testar (default: todas as vagas abertas)'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=20,
            help='Número máximo de candidatos por vaga (default: 20)'
        )
        parser.add_argument(
            '--sem-auditoria',
            action='store_true',
            help='Não salvar resultados na tabela AuditoriaMatch'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar detalhes completos de cada candidato'
        )
        # Nota: Django já tem --no-color built-in, não precisa definir
        parser.add_argument(
            '--score-minimo',
            type=float,
            default=40.0,
            help='Score mínimo para exibir candidato (default: 40)'
        )

    def handle(self, *args, **options):
        # Configurar cores (Django fornece --no-color automaticamente)
        if options.get('no_color') or not sys.stdout.isatty():
            Colors.disable()

        self.verbose = options['verbose']
        self.limite = options['limite']
        self.salvar_auditoria = not options['sem_auditoria']
        self.score_minimo = options['score_minimo']

        # Header
        self._print_header()

        # Determinar vagas a testar
        if options['vaga']:
            try:
                vagas = [Vaga.objects.get(pk=options['vaga'])]
            except Vaga.DoesNotExist:
                raise CommandError(f"Vaga com ID {options['vaga']} não encontrada")
        else:
            vagas = Vaga.objects.filter(status='aberta').order_by('-created_at')[:5]
            if not vagas:
                vagas = Vaga.objects.all().order_by('-created_at')[:5]

        if not vagas:
            self.stdout.write(Colors.RED + "Nenhuma vaga encontrada no banco." + Colors.ENDC)
            return

        # Executar matching para cada vaga
        engine = MatchingEngine(score_minimo=self.score_minimo)

        for vaga in vagas:
            self._testar_vaga(engine, vaga)

        # Footer
        self._print_footer()

    def _print_header(self):
        """Imprime cabeçalho do relatório."""
        self.stdout.write("")
        self.stdout.write(Colors.BOLD + "=" * 80 + Colors.ENDC)
        self.stdout.write(
            Colors.BOLD + Colors.CYAN +
            "  HRTech - Teste do Algoritmo de Matching" +
            Colors.ENDC
        )
        self.stdout.write(
            Colors.DIM +
            f"  Versão do algoritmo: {VERSAO_ALGORITMO}" +
            Colors.ENDC
        )
        self.stdout.write(Colors.BOLD + "=" * 80 + Colors.ENDC)
        self.stdout.write("")

    def _print_footer(self):
        """Imprime rodapé do relatório."""
        self.stdout.write("")
        self.stdout.write(Colors.BOLD + "=" * 80 + Colors.ENDC)
        self.stdout.write(
            Colors.DIM +
            "  Legenda: Camada 1 (60%) = Skills Diretas | " +
            "Camada 2 (25%) = Similaridade | Camada 3 (15%) = Perfil" +
            Colors.ENDC
        )
        if self.salvar_auditoria:
            self.stdout.write(
                Colors.GREEN +
                "  ✓ Resultados salvos na tabela AuditoriaMatch" +
                Colors.ENDC
            )
        self.stdout.write(Colors.BOLD + "=" * 80 + Colors.ENDC)
        self.stdout.write("")

    def _testar_vaga(self, engine: MatchingEngine, vaga: Vaga):
        """Executa matching para uma vaga e exibe resultados."""
        self.stdout.write("")
        self.stdout.write(Colors.BOLD + "-" * 80 + Colors.ENDC)
        self.stdout.write(
            Colors.BOLD + Colors.BLUE +
            f"  VAGA: {vaga.titulo}" +
            Colors.ENDC
        )
        self.stdout.write(
            f"  {Colors.DIM}ID: {vaga.id} | "
            f"Área: {vaga.area} | "
            f"Senioridade: {vaga.senioridade_desejada}{Colors.ENDC}"
        )

        # Mostrar skills da vaga
        skills_obr = [s['nome'] for s in vaga.skills_obrigatorias] if vaga.skills_obrigatorias else []
        skills_des = [s['nome'] for s in vaga.skills_desejaveis] if vaga.skills_desejaveis else []
        self.stdout.write(
            f"  {Colors.DIM}Skills obrigatórias: {', '.join(skills_obr) or 'Nenhuma'}{Colors.ENDC}"
        )
        self.stdout.write(
            f"  {Colors.DIM}Skills desejáveis: {', '.join(skills_des) or 'Nenhuma'}{Colors.ENDC}"
        )
        self.stdout.write(Colors.BOLD + "-" * 80 + Colors.ENDC)

        try:
            resultados = engine.executar_matching(
                vaga_id=vaga.id,
                salvar_auditoria=self.salvar_auditoria,
                limite=self.limite
            )
        except Exception as e:
            self.stdout.write(Colors.RED + f"  ERRO: {e}" + Colors.ENDC)
            return

        if not resultados:
            self.stdout.write(
                Colors.YELLOW +
                f"  Nenhum candidato com score >= {self.score_minimo}" +
                Colors.ENDC
            )
            return

        self.stdout.write(f"\n  {Colors.BOLD}RANKING ({len(resultados)} candidatos):{Colors.ENDC}\n")

        # Cabeçalho da tabela
        self.stdout.write(
            f"  {'#':>3} | "
            f"{'Score':>6} | "
            f"{'C1':>5} {'C2':>5} {'C3':>5} | "
            f"{'Nome':<30} | "
            f"{'Senioridade':<10} | "
            f"{'Disp.':>5}"
        )
        self.stdout.write("  " + "-" * 90)

        for i, resultado in enumerate(resultados, 1):
            cor = score_color(resultado.score_final)
            disponivel = "Sim" if resultado.candidato_disponivel else "Não"

            self.stdout.write(
                f"  {cor}{i:>3}{Colors.ENDC} | "
                f"{cor}{resultado.score_final:>5.1f}{Colors.ENDC}% | "
                f"{resultado.score_camada_1:>5.1f} "
                f"{resultado.score_camada_2:>5.1f} "
                f"{resultado.score_camada_3:>5.1f} | "
                f"{resultado.candidato_nome:<30} | "
                f"{resultado.candidato_senioridade:<10} | "
                f"{disponivel:>5}"
            )

            if self.verbose:
                self._print_candidato_detalhes(resultado)

        # Estatísticas rápidas
        scores = [r.score_final for r in resultados]
        self.stdout.write("")
        self.stdout.write(
            f"  {Colors.DIM}Estatísticas: "
            f"Maior={max(scores):.1f}% | "
            f"Média={sum(scores)/len(scores):.1f}% | "
            f"Menor={min(scores):.1f}%{Colors.ENDC}"
        )

    def _print_candidato_detalhes(self, resultado):
        """Imprime detalhes completos de um candidato (modo verbose)."""
        self.stdout.write("")

        # Skills matched
        if resultado.skills_matched:
            self.stdout.write(f"      {Colors.DIM}Skills matched:{Colors.ENDC}")
            for sm in resultado.skills_matched[:5]:  # Limitar para não poluir
                tipo = "direto" if sm.match_direto else f"similar ({sm.skill_similar})"
                decaimento = f" [-{sm.anos_inativo}a]" if sm.anos_inativo > 0 else ""
                self.stdout.write(
                    f"        - {sm.nome}: nível {sm.nivel_candidato}{decaimento} ({tipo})"
                )

        # Gap analysis
        gap = resultado.gap_analysis
        if gap.skills_ausentes:
            self.stdout.write(
                f"      {Colors.RED}Skills ausentes: {', '.join(gap.skills_ausentes)}{Colors.ENDC}"
            )
        if gap.skills_abaixo_nivel:
            nomes = [s['nome'] for s in gap.skills_abaixo_nivel]
            self.stdout.write(
                f"      {Colors.YELLOW}Abaixo do nível: {', '.join(nomes)}{Colors.ENDC}"
            )

        # Texto explicativo
        self.stdout.write(f"      {Colors.DIM}{gap.texto_explicativo}{Colors.ENDC}")
        self.stdout.write("      " + "-" * 60)
