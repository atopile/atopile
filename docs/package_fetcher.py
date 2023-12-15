import requests
import yaml

gitlab_api = 'https://gitlab.atopile.io/api/v4/'

# Get the list of all projects on our gitlab instance
response = requests.get(f"{gitlab_api}/projects/")
projects = response.json()

# collect the packges that will be added to the docs
packages_to_add = {}
for project in projects:
    if project['namespace']['name'] != 'packages':
        continue
    project_id = project['id']
    project_name = project['name']

    readme_url = f"{gitlab_api}/projects/{project_id}/repository/files/README%2Emd/raw"

    readme_response = requests.get(readme_url)

    if readme_response.status_code == 200:
        with open(f"docs/readme_{project_name}.md", 'w') as file:
            file.write(readme_response.text)
        packages_to_add[project_name] = f"readme_{project_name}.md"
    else:
        print(f"README not found for {project_name}")


def load_yaml_as_dict(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def export_dict_to_yaml(data, file_path):
    with open(file_path, 'w') as file:
        yaml.dump(data, file)

# load the existing mkdocs.yaml
mkdocs_yaml_dict = load_yaml_as_dict('mkdocs.yml')
with open('mkdocs.yml', 'r') as file:
    # load the existing mkdocs.yaml
    mkdocs_yaml_dict = yaml.safe_load(file)
    package_list = []
    for package_name, package_file_path in packages_to_add.items():
        package_list.append({package_name : package_file_path})
    mkdocs_yaml_dict['nav'][1]['Modules'] = package_list

with open('mkdocs.yml', 'w') as file:
    yaml.dump(mkdocs_yaml_dict, file)
