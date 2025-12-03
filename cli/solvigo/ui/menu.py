"""Menu definitions and flow control"""
import questionary
from typing import Optional
from enum import Enum

from solvigo.ui.prompts import solvigo_style


class MenuAction(Enum):
    """Menu actions - simplified"""
    SETUP = "setup"
    DEPLOY = "deploy"
    EXIT = "exit"


# Deploy menu (setup complete)
DEPLOY_MENU = [
    ('Deploy infrastructure', MenuAction.DEPLOY),
    ('Exit', MenuAction.EXIT),
]

# Setup required menu
SETUP_MENU = [
    ('Setup infrastructure', MenuAction.SETUP),
    ('Exit', MenuAction.EXIT),
]


def show_main_menu(setup_complete: bool, project_name: Optional[str] = None) -> MenuAction:
    """
    Display main menu based on setup state.

    Args:
        setup_complete: Whether project setup is complete
        project_name: Name of the project

    Returns:
        MenuAction enum value for the selected action
    """
    if setup_complete:
        menu_items = DEPLOY_MENU
        message = f"Project: {project_name}" if project_name else "What would you like to do?"
    else:
        menu_items = SETUP_MENU
        message = f"Project: {project_name} (setup required)" if project_name else "What would you like to do?"

    choices = [label for label, _ in menu_items]
    action_map = {label: action for label, action in menu_items}

    result = questionary.select(
        message,
        choices=choices,
        style=solvigo_style
    ).ask()

    if not result:
        return MenuAction.EXIT

    return action_map.get(result, MenuAction.EXIT)


def prompt_create_or_exit() -> bool:
    """
    Prompt user to create new project or exit.

    Returns:
        True if user wants to create project, False to exit
    """
    choices = ['Create new project', 'Exit']

    result = questionary.select(
        "What would you like to do?",
        choices=choices,
        style=solvigo_style
    ).ask()

    return result and 'Create' in result
