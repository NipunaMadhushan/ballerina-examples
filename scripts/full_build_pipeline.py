import json
import requests
import os
import sys
import urllib.request as urllib2

stdlib_modules_json_file = 'https://raw.githubusercontent.com/ballerina-platform/ballerina-release/master/' + \
                           'dependabot/resources/extensions.json'

exit_code = 0

def main():
    global exit_code

    _, ballerina_lang_branch, enable_tests, build_level = sys.argv

    stdlib_versions, build_modules = get_module_data(ballerina_lang_branch, build_level)




def get_module_data(ballerina_lang_branch, build_level):
    stdlib_versions = dict()
    build_modules = []

    lang_version = get_version('ballerina-lang', ballerina_lang_branch)
    stdlib_versions['ballerinaLangVersion'] = lang_version

    try:
        response = requests.get(url=stdlib_modules_json_file)

        if response.status_code == 200:
            stdlib_modules_data = json.loads(response.text)
            for module in stdlib_modules_data['standard_library']:
                module_name = module['name']
                module_level = module['level']
                version_key = module['version_key']
                module_version = get_version(module_name, 'master')

                stdlib_versions[version_key] = module_version

                if module_level == build_level:
                    build_modules.append(module_name)

        else:
            print('Failed to access standard library dependency data from', stdlib_modules_json_file)
            sys.exit(1)

    except json.decoder.JSONDecodeError:
        print('Failed to load standard library dependency data')
        sys.exit(1)

    return stdlib_versions, build_modules


def get_version(module_name, branch):
    url = 'https://raw.githubusercontent.com/ballerina-platform/' + module_name + '/' + branch + '/gradle.properties'
    try:
        data = urllib2.urlopen(url)  # it's a file like object and works just like a file
        for line in data:  # files are iterable
            line = line.decode("utf-8").strip()
            if 'version' in line:
                name, value = line.strip().split("=")
                return value

    except json.decoder.JSONDecodeError:
        print('Failed to load standard library dependency data')
        sys.exit(1)

    return "Version not found"


def clone_modules(build_modules):
    global exit_code

    # Clone standard library repos
    for module_name in build_modules:
        exit_code = os.system(f"git clone https://github.com/ballerina-platform/{module_name}.git")
        if exit_code != 0:
            sys.exit(1)


def update_dependency_versions():
    



def build_stdlib_level():


