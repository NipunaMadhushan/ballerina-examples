import json
import requests
import os
import sys


stdlib_modules_by_level = dict()
stdlib_modules_json_file = 'https://raw.githubusercontent.com/ballerina-platform/ballerina-standard-library/' \
                               'main/release/resources/stdlib_modules.json'
stdlib_module_versions = dict()
enable_tests = 'true'
exit_code = 0

#ballerina_bot_username = os.environ['BALLERINA_BOT_USERNAME']
#ballerina_bot_token = os.environ['BALLERINA_BOT_TOKEN']
ballerina_bot_username = "NipunaMadhushan"
ballerina_bot_token = "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"


def main():
    global stdlib_modules_by_level
    global stdlib_modules_json_file
    global stdlib_module_versions
    global enable_tests

    if len(sys.argv) > 0:
        enable_tests = sys.argv[1]

    read_stdlib_modules()
    if stdlib_modules_by_level:
        #clone_repositories()
        #change_version_to_snapshot()
        build_stdlib_repositories(enable_tests)
    else:
        print('Could not find standard library dependency data from', stdlib_modules_json_file)


def read_stdlib_modules():
    try:
        response = requests.get(url=stdlib_modules_json_file)

        if response.status_code == 200:
            stdlib_modules_data = json.loads(response.text)
            read_dependency_data(stdlib_modules_data)
        else:
            print('Failed to access standard library dependency data from', stdlib_modules_json_file)
            sys.exit(1)

    except json.decoder.JSONDecodeError:
        print('Failed to load standard library dependency data')
        sys.exit(1)


def read_dependency_data(stdlib_modules_data):
    for module in stdlib_modules_data['modules']:
        parent = module['name']
        level = module['level']
        stdlib_modules_by_level[level] = stdlib_modules_by_level.get(level, []) + [parent]


def clone_repositories():
    global exit_code

    # Clone standard library repos
    for level in stdlib_modules_by_level:
        stdlib_modules = stdlib_modules_by_level[level]
        for module in stdlib_modules:
            exit_code = os.system(f"git clone https://github.com/ballerina-platform/{module}.git")
            if exit_code != 0:
                sys.exit(1)
        

def build_stdlib_repositories(enable_tests):
    global exit_code

    cmd_exclude_tests = ''
    if enable_tests == 'false':
        cmd_exclude_tests = ' -x test'
        print("Tests are disabled")
    else:
        print("Tests are enabled")

    # Build standard library repos
    for level in stdlib_modules_by_level:
        stdlib_modules = stdlib_modules_by_level[level]
        for module in stdlib_modules:
            os.system(f"echo Building Standard Library Module: {module}")
            exit_code = os.system(f"cd {module};" +
                                  f"export packageUser={ballerina_bot_username};" +
                                  f"export packagePAT={ballerina_bot_token};" +
                                  f"./gradlew clean build{cmd_exclude_tests} --stacktrace --scan")
            if exit_code != 0:
                write_failed_module(module)
                print(f"Build failed for {module}")
                sys.exit(1)


def change_version_to_snapshot():
    lang_version = "2201.0.2-20220315-112900-634fa780"

    print("Lang Version:", lang_version)

    # Change dependent stdlib_module_versions & ballerina-lang version to SNAPSHOT in the stdlib modules
    for level in stdlib_modules_by_level:
        stdlib_modules = stdlib_modules_by_level[level]
        for module in stdlib_modules:
            try:
                properties = dict()
                with open(f"{module}/gradle.properties", 'r') as config_file:
                    for line in config_file:
                        try:
                            name, value = line.split("=")
                            if "ballerinaLangVersion" in name:
                                value = lang_version + "\n"
                            properties[name] = value
                        except ValueError:
                            continue
                    config_file.close()

                with open(f"{module}/gradle.properties", 'w') as config_file:
                    for prop in properties:
                        config_file.write(prop + "=" + properties[prop])
                    config_file.close()

            except FileNotFoundError:
                print(f"Cannot find the gradle.properties file for {module}")
                sys.exit(1)


def write_failed_module(module_name):
    with open("failed_module.txt", "w") as file:
        file.writelines(module_name)
        file.close()


main()
