from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_lgpd_e_organization_campos'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='candidato',
            index=models.Index(fields=['organization', 'status_cv'], name='idx_cand_org_status'),
        ),
        migrations.AddIndex(
            model_name='candidato',
            index=models.Index(fields=['organization', 'created_at'], name='idx_cand_org_created'),
        ),
        migrations.AddIndex(
            model_name='auditoriamatch',
            index=models.Index(fields=['organization', 'created_at'], name='idx_audit_org_created'),
        ),
        migrations.AddIndex(
            model_name='auditoriamatch',
            index=models.Index(fields=['organization', 'vaga'], name='idx_audit_org_vaga'),
        ),
    ]
