"""
Interactive prompts using questionary
"""
import questionary
from questionary import Style
from typing import List, Dict, Optional
from rich.console import Console

console = Console()

# Custom style for Solvigo CLI
solvigo_style = Style([
    ('qmark', 'fg:#00FFFF bold'),       # Cyan question mark
    ('question', 'bold'),                # Bold question text
    ('answer', 'fg:#00FF00 bold'),      # Green answers
    ('pointer', 'fg:#00FFFF bold'),     # Cyan pointer
    ('highlighted', 'fg:#00FFFF bold'), # Cyan highlighted
    ('selected', 'fg:#00FF00'),         # Green selected
    ('separator', 'fg:#555555'),        # Gray separator
    ('instruction', 'fg:#888888'),      # Gray instructions
])


def main_menu(project_detected: bool = False, client: str = None, project: str = None) -> str:
    """
    Display main menu and get user choice.

    Args:
        project_detected: Whether a project was detected
        client: Client name if detected
        project: Project name if detected

    Returns:
        User's choice
    """
    if project_detected:
        choices = [
            '✨ Add services to Terraform',
            '🚀 Deploy infrastructure',
            '📊 View project status',
            '🔧 Configure settings',
            '🆕 Create new project',
            '📁 Choose different project',
            '📥 Import existing GCP project',
            '❌ Exit'
        ]
        message = f"What would you like to do with {client}/{project}?"
    else:
        choices = [
            '🆕 Create new project',
            '📁 Choose existing project',
            '📥 Import existing GCP project',
            '🔧 Setup new client',
            '❌ Exit'
        ]
        message = "What would you like to do?"

    return questionary.select(
        message,
        choices=choices,
        style=solvigo_style
    ).ask()


def select_cloud_run_services(services: List[Dict], client: str = None, project: str = None) -> List[Dict]:
    """
    Let user select Cloud Run services and configure them.

    Args:
        services: List of discovered Cloud Run services

    Returns:
        List of selected and configured services
    """
    if not services:
        return []

    # Create choices with additional info
    choices = []
    for service in services:
        region = service.get('region', 'unknown')
        service_type = service.get('type', 'unknown')
        label = f"{service['name']} ({region}) [{service_type}]"
        choices.append({'name': label, 'value': service, 'checked': True})

    # Add "Create new" option
    if client and project:
        choices.append({
            'name': '+ Create new Cloud Run service',
            'value': {'_new': True, 'type': 'cloud_run'},
            'checked': False
        })

    selected = questionary.checkbox(
        'Select Cloud Run services:',
        choices=choices,
        style=solvigo_style
    ).ask()

    if not selected:
        return []

    # For each selected service, configure or create
    configured = []
    for service in selected:
        # Handle "Create new" selection
        if service.get('_new'):
            new_service = create_new_cloud_run_prompt(client, project)
            if new_service:
                configured.append(new_service)
            continue

        # Configure existing service
        if service.get('type') == 'unknown':
            service_type = questionary.select(
                f"What type is {service['name']}?",
                choices=[
                    'Frontend',
                    'Backend',
                    'Fullstack'
                ],
                style=solvigo_style
            ).ask()
            service['type'] = service_type.lower()

        # Ask about load balancer registration
        register_lb = questionary.confirm(
            f"Register {service['name']} with load balancer?",
            default=True,
            style=solvigo_style
        ).ask()

        service['register_lb'] = register_lb

        if register_lb:
            # Ask for hostname
            default_hostname = f"{service['name']}.{service.get('client', 'client')}.solvigo.ai"
            hostname = questionary.text(
                f"Hostname for {service['name']}:",
                default=default_hostname,
                style=solvigo_style
            ).ask()

            service['hostname'] = hostname

            # Ask about CDN
            enable_cdn = questionary.confirm(
                "Enable Cloud CDN?",
                default=(service['type'] == 'frontend'),
                style=solvigo_style
            ).ask()

            service['enable_cdn'] = enable_cdn

        configured.append(service)

    return configured


def select_resources(resources: Dict[str, List], client: str = None, project: str = None) -> Dict[str, List]:
    """
    Let user select which resources to import.

    Args:
        resources: Dict of resource types to lists of resources

    Returns:
        Dict of selected resources
    """
    selected = {}

    # Store client/project for "create new" prompts
    resources['_client'] = client
    resources['_project'] = project

    # Cloud Run services (with special handling and "create new" option)
    if resources.get('cloud_run') or (client and project):
        selected['cloud_run'] = select_cloud_run_services(
            resources.get('cloud_run', []),
            client=client,
            project=project
        )

    # Database selection (Cloud SQL and Firestore combined)
    if resources.get('cloud_sql') or resources.get('firestore') or (client and project):
        console.print("\n[bold cyan]Database Configuration[/bold cyan]\n")

        db_choices = []

        # Add existing Cloud SQL instances
        for db in resources.get('cloud_sql', []):
            db_choices.append({
                'name': f"Cloud SQL: {db['name']} ({db['database_version']}, {db['tier']})",
                'value': {'type': 'cloud_sql', 'data': db},
                'checked': True
            })

        # Add existing Firestore databases
        for db in resources.get('firestore', []):
            db_choices.append({
                'name': f"Firestore: {db.get('name', 'default')}",
                'value': {'type': 'firestore', 'data': db},
                'checked': True
            })

        # Add "Create new" options
        if client and project:
            db_choices.append({
                'name': '+ Create new Cloud SQL (PostgreSQL/MySQL)',
                'value': {'_new': True, 'type': 'cloud_sql'},
                'checked': False
            })

            db_choices.append({
                'name': '+ Create new Firestore database',
                'value': {'_new': True, 'type': 'firestore'},
                'checked': False
            })

        # Add "No database" option
        db_choices.append({
            'name': '○ Skip database (no database needed)',
            'value': {'_skip': True},
            'checked': False
        })

        if db_choices:
            selected_dbs = questionary.checkbox(
                'Select databases (or skip):',
                choices=db_choices,
                style=solvigo_style
            ).ask()

            if selected_dbs:
                # Separate Cloud SQL and Firestore
                cloud_sql_list = []
                firestore_list = []

                for db_item in selected_dbs:
                    if db_item.get('_skip'):
                        continue  # User chose no database

                    if db_item.get('_new'):
                        # Create new database
                        if db_item['type'] == 'cloud_sql':
                            new_db = create_new_cloud_sql_prompt(client, project)
                            if new_db:
                                cloud_sql_list.append(new_db)
                        elif db_item['type'] == 'firestore':
                            new_db = create_new_firestore_prompt(client, project)
                            if new_db:
                                firestore_list.append(new_db)
                    else:
                        # Existing database
                        if db_item['type'] == 'cloud_sql':
                            cloud_sql_list.append(db_item['data'])
                        elif db_item['type'] == 'firestore':
                            firestore_list.append(db_item['data'])

                if cloud_sql_list:
                    selected['cloud_sql'] = cloud_sql_list
                if firestore_list:
                    selected['firestore'] = firestore_list

    # Storage buckets
    if resources.get('storage') or True:  # Always show even if no existing buckets
        choices = [
            {
                'name': f"{bucket['name']} ({bucket.get('location', 'unknown')})" +
                        (" [Terraform state - skip?]" if bucket.get('is_terraform_state') else ""),
                'value': bucket,
                'checked': not bucket.get('is_terraform_state', False)
            }
            for bucket in resources.get('storage', [])
        ]

        # Add "Create new bucket" option
        client = resources.get('_client', 'client')
        project = resources.get('_project', 'project')

        choices.append({
            'name': '+ Create new bucket',
            'value': {'_new': True, 'type': 'bucket'},
            'checked': False
        })

        selected_buckets = questionary.checkbox(
            'Select storage buckets:',
            choices=choices,
            style=solvigo_style
        ).ask()

        if selected_buckets:
            # Handle "Create new" selections
            final_buckets = []
            for bucket in selected_buckets:
                if bucket.get('_new'):
                    # Prompt for new bucket details
                    new_bucket = create_new_bucket_prompt(client, project)
                    if new_bucket:
                        final_buckets.append(new_bucket)
                else:
                    final_buckets.append(bucket)

            selected['storage'] = final_buckets

    # Secrets
    if resources.get('secrets'):
        # For many secrets, offer "select all" option first
        if len(resources['secrets']) > 5:
            select_all = questionary.confirm(
                f'Select all {len(resources["secrets"])} secrets?',
                default=True,
                style=solvigo_style
            ).ask()

            if select_all:
                selected['secrets'] = resources['secrets']
            else:
                choices = [
                    {'name': secret['name'], 'value': secret, 'checked': True}
                    for secret in resources['secrets']
                ]
                selected_secrets = questionary.checkbox(
                    'Select secrets:',
                    choices=choices,
                    style=solvigo_style
                ).ask()
                selected['secrets'] = selected_secrets or []
        else:
            choices = [
                {'name': secret['name'], 'value': secret, 'checked': True}
                for secret in resources['secrets']
            ]
            selected_secrets = questionary.checkbox(
                'Select secrets:',
                choices=choices,
                style=solvigo_style
            ).ask()
            selected['secrets'] = selected_secrets or []

    # Service accounts
    if resources.get('service_accounts'):
        choices = [
            {'name': sa['email'], 'value': sa, 'checked': True}
            for sa in resources['service_accounts']
        ]

        if choices:
            selected_sas = questionary.checkbox(
                'Select service accounts:',
                choices=choices,
                style=solvigo_style
            ).ask()
            selected['service_accounts'] = selected_sas or []

    # APIs
    if resources.get('apis'):
        choices = [
            {'name': f"{api['title']} ({api['name']})", 'value': api, 'checked': True}
            for api in resources['apis']
        ]

        if choices:
            selected_apis = questionary.checkbox(
                'Select APIs to include in Terraform:',
                choices=choices,
                style=solvigo_style
            ).ask()
            selected['apis'] = selected_apis or []

    return selected


def confirm_action(message: str, default: bool = True) -> bool:
    """Confirm an action with the user."""
    return questionary.confirm(
        message,
        default=default,
        style=solvigo_style
    ).ask()


def text_input(message: str, default: str = "", validate=None) -> str:
    """Get text input from user."""
    return questionary.text(
        message,
        default=default,
        validate=validate,
        style=solvigo_style
    ).ask()


def create_new_bucket_prompt(client: str, project: str) -> Optional[Dict]:
    """
    Prompt user to create a new storage bucket.

    Args:
        client: Client name
        project: Project name

    Returns:
        Dict with bucket configuration or None if cancelled
    """
    console.print("\n[cyan]Create New Storage Bucket[/cyan]\n")

    # Suggest bucket names based on common use cases
    suggested_names = [
        f"{client}-{project}-uploads",
        f"{client}-{project}-static",
        f"{client}-{project}-backups",
        f"{client}-{project}-data",
    ]

    bucket_type = select_option(
        "Bucket purpose:",
        choices=[
            "User uploads",
            "Static assets",
            "Backups",
            "Data storage",
            "Custom"
        ]
    )

    # Get default name based on type
    type_map = {
        "User uploads": f"{client}-{project}-uploads",
        "Static assets": f"{client}-{project}-static",
        "Backups": f"{client}-{project}-backups",
        "Data storage": f"{client}-{project}-data",
    }

    default_name = type_map.get(bucket_type, f"{client}-{project}-bucket")

    bucket_name = text_input(
        "Bucket name (globally unique):",
        default=default_name
    )

    # Location selection with autocomplete
    location = questionary.autocomplete(
        "Bucket location:",
        choices=[
            "europe-north2 (Stockholm) [recommended]",
            "europe-north1 (Finland)",
            "europe-west1 (Belgium)",
            "europe-west4 (Netherlands)",
            "Multi-region: EU",
            "Multi-region: US",
            "Multi-region: ASIA"
        ],
        default="europe-north2 (Stockholm) [recommended]",
        style=solvigo_style
    ).ask()

    location_map = {
        "europe-north2 (Stockholm) [recommended]": "europe-north2",
        "europe-north1 (Finland)": "europe-north1",
        "europe-west1 (Belgium)": "europe-west1",
        "europe-west4 (Netherlands)": "europe-west4",
        "Multi-region: EU": "EU",
        "Multi-region: US": "US",
        "Multi-region: ASIA": "ASIA"
    }

    return {
        'name': bucket_name,
        'location': location_map[location],
        'purpose': bucket_type,
        '_new': True,
        '_create': True
    }


def create_new_firestore_prompt(client: str, project: str) -> Optional[Dict]:
    """
    Prompt user to create a new Firestore database.

    Args:
        client: Client name
        project: Project name

    Returns:
        Dict with Firestore configuration or None if cancelled
    """
    console.print("\n[cyan]Create New Firestore Database[/cyan]\n")

    db_mode = select_option(
        "Firestore mode:",
        choices=[
            "Native mode (recommended for new apps)",
            "Datastore mode (for legacy compatibility)"
        ]
    )

    location = select_option(
        "Database location:",
        choices=[
            "eur3 (Europe multi-region)",
            "europe-north1 (Finland)",
            "europe-west1 (Belgium)"
        ]
    )

    location_map = {
        "eur3 (Europe multi-region)": "eur3",
        "europe-north1 (Finland)": "europe-north1",
        "europe-west1 (Belgium)": "europe-west1"
    }

    return {
        'name': '(default)',
        'mode': 'FIRESTORE_NATIVE' if 'Native' in db_mode else 'DATASTORE_MODE',
        'location': location_map[location],
        '_new': True,
        '_create': True
    }


def create_new_cloud_sql_prompt(client: str, project: str) -> Optional[Dict]:
    """
    Prompt user to create a new Cloud SQL database.

    Args:
        client: Client name
        project: Project name

    Returns:
        Dict with Cloud SQL configuration or None if cancelled
    """
    console.print("\n[cyan]Create New Cloud SQL Database[/cyan]\n")

    instance_name = text_input(
        "Instance name:",
        default=f"{project}-db"
    )

    db_type = select_option(
        "Database type:",
        choices=[
            "PostgreSQL 15 (recommended)",
            "PostgreSQL 14",
            "PostgreSQL 16",
            "MySQL 8.0"
        ]
    )

    # Map to version strings
    version_map = {
        "PostgreSQL 15 (recommended)": "POSTGRES_15",
        "PostgreSQL 14": "POSTGRES_14",
        "PostgreSQL 16": "POSTGRES_16",
        "MySQL 8.0": "MYSQL_8_0"
    }

    tier = select_option(
        "Instance size (can be changed later in Terraform):",
        choices=[
            "Small (recommended) - 0.6GB RAM, €7-15/month",
            "Medium - 3.75GB RAM, €46/month",
            "Large - 7.5GB RAM, €92/month"
        ]
    )

    # Map to actual GCP machine types
    tier_map = {
        "Small (recommended) - 0.6GB RAM, €7-15/month": "db-g1-small",  # 1.7GB RAM, shared CPU
        "Medium - 3.75GB RAM, €46/month": "db-n1-standard-1",  # 1 vCPU, 3.75GB RAM
        "Large - 7.5GB RAM, €92/month": "db-n1-standard-2"     # 2 vCPU, 7.5GB RAM
    }

    console.print("\n[dim]Note: Instance size can be easily changed later in the Terraform configuration[/dim]")

    # Region selection with autocomplete/search
    region = questionary.autocomplete(
        "Region:",
        choices=[
            "europe-north2 (Stockholm) [recommended]",
            "europe-north1 (Finland)",
            "europe-west1 (Belgium)",
            "europe-west4 (Netherlands)",
            "europe-west2 (London)",
            "us-central1 (Iowa)",
            "us-east1 (South Carolina)",
            "us-west1 (Oregon)",
            "asia-northeast1 (Tokyo)",
            "asia-southeast1 (Singapore)"
        ],
        default="europe-north2 (Stockholm) [recommended]",
        style=solvigo_style
    ).ask()

    # Map display names to region codes
    region_code_map = {
        "europe-north2 (Stockholm) [recommended]": "europe-north2",
        "europe-north1 (Finland)": "europe-north1",
        "europe-west1 (Belgium)": "europe-west1",
        "europe-west4 (Netherlands)": "europe-west4",
        "europe-west2 (London)": "europe-west2",
        "us-central1 (Iowa)": "us-central1",
        "us-east1 (South Carolina)": "us-east1",
        "us-west1 (Oregon)": "us-west1",
        "asia-northeast1 (Tokyo)": "asia-northeast1",
        "asia-southeast1 (Singapore)": "asia-southeast1"
    }

    backups = confirm_action(
        "Enable automated backups?",
        default=True
    )

    return {
        'name': instance_name,
        'database_version': version_map[db_type],
        'tier': tier_map[tier],
        'region': region_code_map.get(region, 'europe-north2'),
        'backups': backups,
        '_new': True,
        '_create': True
    }


def create_new_cloud_run_prompt(client: str, project: str) -> Optional[Dict]:
    """
    Prompt user to create a new Cloud Run service.

    Args:
        client: Client name
        project: Project name

    Returns:
        Dict with Cloud Run configuration or None if cancelled
    """
    console.print("\n[cyan]Create New Cloud Run Service[/cyan]\n")

    service_name = text_input(
        "Service name:",
        default=f"{project}-app"
    )

    service_type = select_option(
        "Service type:",
        choices=["Frontend", "Backend", "Fullstack"]
    )

    region = select_option(
        "Region:",
        choices=[
            "europe-north2 (Stockholm)",
            "europe-north1 (Finland)",
            "europe-west1 (Belgium)"
        ]
    )

    region_map = {
        "europe-north2 (Stockholm)": "europe-north2",
        "europe-north1 (Finland)": "europe-north1",
        "europe-west1 (Belgium)": "europe-west1"
    }

    # Register with LB
    register_lb = confirm_action(
        "Register with load balancer?",
        default=True
    )

    hostname = None
    enable_cdn = False

    if register_lb:
        hostname = text_input(
            "Hostname:",
            default=f"{service_name}.{client}.solvigo.ai"
        )

        enable_cdn = confirm_action(
            "Enable Cloud CDN?",
            default=(service_type.lower() == 'frontend')
        )

    return {
        'name': service_name,
        'type': service_type.lower(),
        'region': region_map[region],
        'register_lb': register_lb,
        'hostname': hostname,
        'enable_cdn': enable_cdn,
        '_new': True,
        '_create': True
    }


def select_option(message: str, choices: List[str], default: Optional[str] = None) -> str:
    """
    Let user select one option from a list using arrow keys.

    Args:
        message: Question to display
        choices: List of options
        default: Default selection (optional)

    Returns:
        Selected option

    Usage:
        - Use arrow keys (↑/↓) to navigate
        - Press Enter to select
        - Type to search (for long lists)
    """
    # For very long lists, use autocomplete (searchable)
    if len(choices) > 36:
        # Add search instruction to message
        search_message = f"{message} (Type to search, use arrow keys)"
        return questionary.autocomplete(
            search_message,
            choices=choices,
            default=default or "",
            style=solvigo_style
        ).ask()

    # For shorter lists, use select with arrow keys
    if len(choices) > 1:
        arrow_message = f"{message} (Use arrow keys)"
    else:
        arrow_message = message

    return questionary.select(
        arrow_message,
        choices=choices,
        default=default,
        style=solvigo_style,
        use_shortcuts=False,  # Disable shortcuts to support more than 36 items
        use_arrow_keys=True
    ).ask()
