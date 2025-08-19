import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_github_actions() -> bool:
    """Check if running in GitHub Actions environment."""
    return os.getenv('GITHUB_ACTIONS') == 'true'


def is_pull_request() -> bool:
    """Check if the current GitHub Actions run is for a pull request."""
    return (
        is_github_actions() and 
        os.getenv('GITHUB_EVENT_NAME') in ['pull_request', 'pull_request_target']
    )


def get_pr_number() -> Optional[int]:
    """Get the PR number from GitHub Actions environment."""
    if not is_pull_request():
        return None
    
    event_path = os.getenv('GITHUB_EVENT_PATH')
    if not event_path:
        return None
    
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
        return event_data.get('pull_request', {}).get('number')
    except Exception as e:
        logger.error(f"Failed to get PR number: {e}")
        return None


def get_repository() -> Optional[str]:
    """Get the repository name from GitHub Actions environment."""
    return os.getenv('GITHUB_REPOSITORY')


def upload_image_to_pr(image_path: Path, pr_number: int, repository: str) -> bool:
    """
    Upload an image to a GitHub PR using GitHub CLI.
    
    Args:
        image_path: Path to the image file
        pr_number: PR number
        repository: Repository in owner/repo format
        
    Returns:
        True if successful, False otherwise
    """
    if not image_path.exists():
        logger.error(f"Image file not found: {image_path}")
        return False
    
    try:
        result = subprocess.run([
            'gh', 'pr', 'comment', str(pr_number),
            '--repo', repository,
            '--body', f'## 3D PCB Render\n\n![3D PCB Render]({image_path.name})'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Successfully added 3D render image to PR #{pr_number}")
            return True
        else:
            logger.error(f"Failed to add image to PR: {result.stderr}")
            return False
            
    except FileNotFoundError:
        logger.error("GitHub CLI (gh) not found")
        return False
    except Exception as e:
        logger.error(f"Failed to upload image to PR: {e}")
        return False


def attach_images_to_pr(image_files: list[Path]) -> bool:
    """
    Attach multiple images to the current PR if running in GitHub Actions.
    
    Args:
        image_files: List of image file paths
        
    Returns:
        True if successful or not in PR context, False if failed
    """
    if not is_pull_request():
        logger.debug("Not in PR context, skipping image attachment")
        return True
    
    pr_number = get_pr_number()
    repository = get_repository()
    
    if not pr_number or not repository:
        logger.warning("Could not determine PR number or repository")
        return False
    
    success = True
    for image_file in image_files:
        if image_file.exists():
            if not upload_image_to_pr(image_file, pr_number, repository):
                success = False
        else:
            logger.warning(f"Image file not found: {image_file}")
    
    return success
