"""Initial registry schema

Revision ID: 001
Revises:
Create Date: 2025-11-18

Creates all tables for the Solvigo platform registry
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Clients table
    op.create_table(
        'clients',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(255), nullable=False, unique=True),
        sa.Column('billing_contact', sa.String(255)),
        sa.Column('technical_contact', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(255)),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('notes', sa.TEXT),
    )
    op.create_index('idx_clients_subdomain', 'clients', ['subdomain'])
    op.create_index('idx_clients_status', 'clients', ['status'])

    # 2. Projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('client_id', sa.String(255), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(255), nullable=False),
        sa.Column('full_domain', sa.String(500), nullable=False, unique=True),

        # GCP Resources
        sa.Column('gcp_project_id', sa.String(255), unique=True),
        sa.Column('gcp_folder_id', sa.String(255)),
        sa.Column('gcp_region', sa.String(50), server_default='europe-north1'),

        # Code & State
        sa.Column('github_repo', sa.String(500)),
        sa.Column('terraform_state_bucket', sa.String(255)),
        sa.Column('terraform_state_prefix', sa.String(255)),

        # Metadata
        sa.Column('project_type', sa.String(50)),  # 'fullstack', 'backend', 'frontend'
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(255)),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.Column('last_deployed_at', sa.TIMESTAMP),
        sa.Column('status', sa.String(50), server_default='active'),

        sa.UniqueConstraint('client_id', 'subdomain', name='uq_client_subdomain')
    )
    op.create_index('idx_projects_client_id', 'projects', ['client_id'])
    op.create_index('idx_projects_full_domain', 'projects', ['full_domain'])
    op.create_index('idx_projects_gcp_project_id', 'projects', ['gcp_project_id'])

    # 3. Environments table
    op.create_table(
        'environments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.String(255), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),  # 'staging', 'prod'

        # Infrastructure
        sa.Column('gcp_project_id', sa.String(255)),  # NULL if same project
        sa.Column('database_instance', sa.String(255)),
        sa.Column('database_name', sa.String(255)),
        sa.Column('database_type', sa.String(50)),  # 'postgresql', 'mysql', 'firestore'

        # Build Configuration
        sa.Column('auto_deploy', sa.Boolean, server_default='false'),
        sa.Column('requires_approval', sa.Boolean, server_default='true'),
        sa.Column('branch_pattern', sa.String(255)),  # '^main$'
        sa.Column('tag_pattern', sa.String(255)),  # '^v[0-9]+\.[0-9]+\.[0-9]+$'

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),

        sa.UniqueConstraint('project_id', 'name', name='uq_project_environment')
    )
    op.create_index('idx_environments_project_id', 'environments', ['project_id'])

    # 4. Services table
    op.create_table(
        'services',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.String(255), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('environment_id', sa.Integer, sa.ForeignKey('environments.id', ondelete='CASCADE')),

        sa.Column('name', sa.String(255), nullable=False),  # 'backend-staging'
        sa.Column('type', sa.String(50), nullable=False),  # 'backend', 'frontend'

        # Cloud Run
        sa.Column('cloud_run_service', sa.String(255)),
        sa.Column('cloud_run_region', sa.String(50)),
        sa.Column('cloud_run_url', sa.String(500)),

        # Build Config
        sa.Column('dockerfile_path', sa.String(500)),
        sa.Column('cloudbuild_file', sa.String(500)),

        # Container Registry
        sa.Column('artifact_registry_repo', sa.String(500)),  # Full AR path

        # Status
        sa.Column('current_image', sa.String(500)),
        sa.Column('current_revision', sa.String(255)),
        sa.Column('last_deployed_at', sa.TIMESTAMP),
        sa.Column('last_deployed_by', sa.String(255)),
        sa.Column('status', sa.String(50), server_default='active'),

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),

        sa.UniqueConstraint('project_id', 'environment_id', 'name', name='uq_project_env_service')
    )
    op.create_index('idx_services_project_id', 'services', ['project_id'])
    op.create_index('idx_services_cloud_run', 'services', ['cloud_run_service'])

    # 5. Deployments table (history)
    op.create_table(
        'deployments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),

        # Build Info
        sa.Column('build_id', sa.String(255)),
        sa.Column('build_trigger', sa.String(255)),
        sa.Column('git_commit_sha', sa.String(40)),
        sa.Column('git_tag', sa.String(255)),
        sa.Column('git_branch', sa.String(255)),
        sa.Column('git_author', sa.String(255)),

        # Deployment
        sa.Column('image', sa.String(500)),
        sa.Column('deployed_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('deployed_by', sa.String(255)),

        # Status
        sa.Column('status', sa.String(50)),  # 'success', 'failed', 'in_progress', 'rolled_back'
        sa.Column('duration_seconds', sa.Integer),
        sa.Column('error_message', sa.TEXT),

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_deployments_service_id', 'deployments', ['service_id'])
    op.create_index('idx_deployments_deployed_at', 'deployments', ['deployed_at'])
    op.create_index('idx_deployments_status', 'deployments', ['status'])

    # 6. Subdomain mappings table (for Load Balancer)
    op.create_table(
        'subdomain_mappings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),

        sa.Column('full_domain', sa.String(500), nullable=False, unique=True),
        sa.Column('backend_service', sa.String(255)),  # GCP backend service name
        sa.Column('cloud_run_neg', sa.String(255)),  # Network Endpoint Group

        # SSL
        sa.Column('ssl_certificate', sa.String(255)),
        sa.Column('ssl_status', sa.String(50)),  # 'active', 'provisioning', 'failed'

        # Load Balancer
        sa.Column('url_map', sa.String(255)),
        sa.Column('path_matcher', sa.String(255)),

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.Column('status', sa.String(50), server_default='active'),
    )
    op.create_index('idx_subdomain_mappings_full_domain', 'subdomain_mappings', ['full_domain'])
    op.create_index('idx_subdomain_mappings_service_id', 'subdomain_mappings', ['service_id'])

    # 7. Infrastructure resources table (track all GCP resources)
    op.create_table(
        'infrastructure_resources',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.String(255), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('environment_id', sa.Integer, sa.ForeignKey('environments.id', ondelete='SET NULL')),

        # Resource Identity
        sa.Column('resource_type', sa.String(100), nullable=False),  # 'cloud_run', 'cloud_sql', 'storage_bucket'
        sa.Column('resource_name', sa.String(255), nullable=False),
        sa.Column('gcp_resource_id', sa.String(500)),  # Full GCP resource path

        # Terraform
        sa.Column('terraform_module', sa.String(255)),
        sa.Column('terraform_resource_address', sa.String(500)),

        # Metadata
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('imported_at', sa.TIMESTAMP),
        sa.Column('last_verified_at', sa.TIMESTAMP),
        sa.Column('configuration', postgresql.JSONB),  # Store resource config

        sa.UniqueConstraint('project_id', 'resource_type', 'resource_name', name='uq_project_resource')
    )
    op.create_index('idx_infra_resources_project_id', 'infrastructure_resources', ['project_id'])
    op.create_index('idx_infra_resources_type', 'infrastructure_resources', ['resource_type'])

    # 8. Users table (access control)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255)),
        sa.Column('role', sa.String(50), nullable=False),  # 'admin', 'consultant', 'viewer'

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('last_login_at', sa.TIMESTAMP),
        sa.Column('status', sa.String(50), server_default='active'),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # 9. Project access table
    op.create_table(
        'project_access',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(255), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50)),  # 'owner', 'editor', 'viewer'
        sa.Column('granted_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('granted_by', sa.String(255)),

        sa.UniqueConstraint('user_id', 'project_id', name='uq_user_project')
    )
    op.create_index('idx_project_access_user_id', 'project_access', ['user_id'])
    op.create_index('idx_project_access_project_id', 'project_access', ['project_id'])

    # 10. Cost allocations table (for billing/dashboards)
    op.create_table(
        'cost_allocations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.String(255), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),

        sa.Column('month', sa.Date, nullable=False),
        sa.Column('total_cost', sa.DECIMAL(10, 2)),

        # Breakdown
        sa.Column('compute_cost', sa.DECIMAL(10, 2)),
        sa.Column('storage_cost', sa.DECIMAL(10, 2)),
        sa.Column('networking_cost', sa.DECIMAL(10, 2)),
        sa.Column('database_cost', sa.DECIMAL(10, 2)),
        sa.Column('other_cost', sa.DECIMAL(10, 2)),

        sa.Column('imported_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('currency', sa.String(3), server_default='USD'),

        sa.UniqueConstraint('project_id', 'month', name='uq_project_month')
    )
    op.create_index('idx_cost_allocations_project_id', 'cost_allocations', ['project_id'])
    op.create_index('idx_cost_allocations_month', 'cost_allocations', ['month'])

    # 11. Audit log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),  # 'create_project', 'deploy_service', etc.
        sa.Column('entity_type', sa.String(100)),  # 'project', 'service', 'client'
        sa.Column('entity_id', sa.String(255)),

        # Change Details
        sa.Column('old_value', postgresql.JSONB),
        sa.Column('new_value', postgresql.JSONB),

        # Context
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('request_id', sa.String(255)),

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_audit_log_user_email', 'audit_log', ['user_email'])
    op.create_index('idx_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'])

    # 12. DNS records table (for tracking and verification)
    op.create_table(
        'dns_records',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('subdomain_mapping_id', sa.Integer, sa.ForeignKey('subdomain_mappings.id', ondelete='CASCADE')),

        sa.Column('record_type', sa.String(10), nullable=False),  # 'A', 'CNAME'
        sa.Column('record_value', sa.String(255), nullable=False),
        sa.Column('ttl', sa.Integer, server_default='300'),

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('verified_at', sa.TIMESTAMP),  # Last DNS propagation check
        sa.Column('status', sa.String(50), server_default='active'),
    )

    # 13. Terraform state metadata table
    op.create_table(
        'terraform_states',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.String(255), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),

        sa.Column('state_bucket', sa.String(255), nullable=False),
        sa.Column('state_prefix', sa.String(255), nullable=False),
        sa.Column('last_applied_at', sa.TIMESTAMP),
        sa.Column('last_applied_by', sa.String(255)),
        sa.Column('resource_count', sa.Integer),

        sa.Column('terraform_version', sa.String(50)),
        sa.Column('state_serial', sa.Integer),  # Terraform state version

        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),

        sa.UniqueConstraint('state_bucket', 'state_prefix', name='uq_state_location')
    )

    # Grant permissions to kristi@solvigo.ai as superadmin
    op.execute("""
        -- Grant all privileges on all tables
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "kristi@solvigo.ai";
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "kristi@solvigo.ai";
        GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "kristi@solvigo.ai";

        -- Also grant to the registry API service account
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "registry-api@solvigo-platform-prod.iam";
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "registry-api@solvigo-platform-prod.iam";
    """)

    # Create initial admin user (kristi@solvigo.ai)
    op.execute("""
        INSERT INTO users (email, name, role, status)
        VALUES ('kristi@solvigo.ai', 'Kristi Francis', 'admin', 'active')
        ON CONFLICT (email) DO NOTHING;
    """)


def downgrade():
    op.drop_table('terraform_states')
    op.drop_table('dns_records')
    op.drop_table('audit_log')
    op.drop_table('cost_allocations')
    op.drop_table('project_access')
    op.drop_table('users')
    op.drop_table('subdomain_mappings')
    op.drop_table('deployments')
    op.drop_table('services')
    op.drop_table('environments')
    op.drop_table('projects')
    op.drop_table('clients')
