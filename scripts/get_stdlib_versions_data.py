import json
import requests
import os
import sys
import urllib.request as urllib2

stdlib_modules_json_file = 'https://raw.githubusercontent.com/ballerina-platform/ballerina-release/master/' + \
                           'dependabot/resources/extensions.json'


def main():
    if len(sys.argv) > 2:
        ballerina_lang_branch = sys.argv[1]
        enable_tests = sys.argv[2]
        stdlib_level = sys.argv[3]

    stdlib_versions = get_module_data()


def get_module_data():
    stdlib_versions = dict()

    try:
        response = requests.get(url=stdlib_modules_json_file)

        if response.status_code == 200:
            stdlib_modules_data = json.loads(response.text)
            for module in stdlib_modules_data['standard_library']:
                module_name = module['name']
                version_key = module['version_key']
                module_version = get_version(module_name, 'master')

                stdlib_versions[version_key] = module_version

        else:
            print('Failed to access standard library dependency data from', stdlib_modules_json_file)
            sys.exit(1)

    except json.decoder.JSONDecodeError:
        print('Failed to load standard library dependency data')
        sys.exit(1)

    return stdlib_versions


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


version = get_version('module-ballerina-http')
print(version)
