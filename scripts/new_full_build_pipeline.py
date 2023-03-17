import argparse
import json
import os
import subprocess
import sys

from colorama import Fore
from colorama import Style
from pathlib import Path
from urllib import request
from configobj import ConfigObj

# Resources
MODULE_LIST_JSON = "https://raw.githubusercontent.com/ballerina-platform/" + \
                   "ballerina-release/master/dependabot/resources/extensions.json"
TEST_IGNORE_MODULES_JSON = "https://raw.githubusercontent.com/ballerina-platform/" + \
                           "dependabot/resources/full_build_ignore_modules.json"

# Credentials
BALLERINA_BOT_USERNAME = os.environ["BALLERINA_BOT_USERNAME"]
BALLERINA_BOT_TOKEN = os.environ["BALLERINA_BOT_TOKEN"]

# Repository names
BALLERINA_LANG_REPO_NAME = "ballerina-lang"
BALLERINA_DIST_REPO_NAME = "ballerina-distribution"

# File names
GRADLE_PROPERTIES = "gradle.properties"
RELEASED_VERSION_PROPERTIES = "released_version.properties"

# Argument parser
parser = argparse.ArgumentParser(description="Full Build Pipeline")

# Mandatory arguments
parser.add_argument('path', help="Path to the directory where the standard library modules are (need to be) cloned")

# Optional arguments
parser.add_argument('--lang-branch', help="ballerina-lang branch to use for the builds (If it is not specified, " +
                                          "master branch will be used as the default branch)")
parser.add_argument('--lang-version', help="ballerina-lang version to use for the builds (If this argument passes, " +
                                           "--lang-branch argument won\'t work)")
parser.add_argument('--downstream-branch', help="Branch to build the downstream modules. (If the branch not found, " +
                                                "the default branch (or branch specified in ignore modules json " +
                                                "file) will be used)")
parser.add_argument('--update-stdlib-dependencies', action="store_true",
                    help="Replace all the standard library dependent versions with 'SNAPSHOT' versions. " +
                         "This is helpful to incrementally build libraries on top of a local change")
parser.add_argument('--use-released-versions', action="store_true",
                    help="Use released versions in " +
                         "https://github.com/ballerina-platform/ballerina-distribution/blob/master/gradle.properties" +
                         " according to the patch level (e.g.; 2201.4.x). Must use '--patch-level' flag to specify " +
                         "patch level")
parser.add_argument('--patch-level', help="Patch level for the build (e.g.; 2201.4.x)")
parser.add_argument('--publish-to-local-central', action="store_true",
                    help="Publish all the modules to the local ballerina central repository")
parser.add_argument('--skip-tests', action="store_true", help="Skip tests in the builds")
parser.add_argument('--github-user', action="store_true",
                    help="Github User to use for ballerina-lang repository")
parser.add_argument('--keep-local-changes', action="store_true",
                    help="Stop updating the repos from the origin. Keep the local changes")
parser.add_argument('--up-to-module', help="Build up to the specified module")
parser.add_argument('--from-module', help="Build from the specified module")
parser.add_argument('--test-module', help="Test the specified module (Only the dependency modules and dependent " +
                                          "modules will be built)")
parser.add_argument('--skip-build-distribution', action="store_true",
                    help="If the distribution build should be skipped.")
parser.add_argument('--additional-commands',
                    help="To provide a custom command to execute inside each repo. Provide this as a " +
                         "string. If not provided './gradlew clean build' will be used")
parser.add_argument('--continue-on-error', action="store_true",
                    help="Whether to continue the subsequent builds when a module build fails")
parser.add_argument('--remove-after-build', action="store_true",
                    help="Remove cloned module after the build")

github_user = 'ballerina-platform'
stdlib_modules_by_level = dict()
stdlib_versions = dict()
released_stdlib_versions = dict()

test_ignore_modules = []
build_ignore_modules = []
downstream_repo_branches = dict()
released_version_data_file_url = None


def main():
    global MODULE_LIST_JSON
    global stdlib_modules_by_level
    global test_ignore_modules
    global build_ignore_modules
    global downstream_repo_branches
    global github_user
    global stdlib_versions
    global released_stdlib_versions
    global released_version_data_file_url

    args = parser.parse_args()
    # Commands to be used to build downstream repositories (Except ballerina-distribution)
    commands = ["./gradlew", "clean", "build", "--stacktrace", "--scan", "--console=plain", "--no-daemon", "--continue"]

    lang_version = None
    downstream_branch = None
    patch_level = None
    
    skip_tests = False
    update_stdlib_dependencies = False
    use_released_versions = False
    keep_local_changes = False

    up_to_module = None
    from_module = None
    test_module = None
    build_distribution = True

    continue_on_error = False
    remove_after_build = False

    released_version_data_file_url = None

    print_block()

    if not args.path:
        print_error("Path to the directory where the standard library modules are (need to be) cloned has not been " +
                    "specified")
        exit(1)

    if not os.path.isdir(args.path):
        print_info("Provided root directory does not exist. Creating the directory and cloning the repositories")
        create_directory(args.path)

    # Change current directory to the specified directory
    os.chdir(args.path)

    if args.github_user:
        print_info("Using github user: " + args.github_user)
        github_user = args.github_user

    if args.keep_local_changes:
        print_info("Not updating the local repositories.")
        keep_local_changes = True
    else:
        print_info("Updating all the repositories. Any local change will be overridden")

    if args.lang_version:
        print_info("Using ballerina lang version: " + args.lang_version)
        lang_version = args.lang_version
    else:
        clone_repository("ballerina-lang")
        if args.lang_branch:
            print_info("Using ballerina lang branch: " + args.lang_branch)
            checkout_branch(lang_branch, keep_local_changes)
        else:
            print_info("Using ballerina lang branch: master (default)")

        os.chdir("ballerina-lang")
        lang_version = get_version()
        lang_build_commands = ["./gradlew", "clean", "build", "-x test", "--scan", "--stacktrace",
                               "publishToMavenLocal"]
        build_module(lang_build_commands)
        os.chdir("..")

    if args.skip_tests:
        print_info("Skipping tests for downstream modules")
        skip_tests = True
        commands.append("-x")
        commands.append("test")

    if args.update_stdlib_dependencies:
        print_info("Using local SNAPSHOT builds for upper level dependencies")
        commands.append("publishToMavenLocal")
        update_stdlib_dependencies = True
    else:
        print_info("Using existing versions for the builds")

    if args.use_released_versions:
        print_info("Using released versions in " +
                   "https://github.com/ballerina-platform/ballerina-distribution/blob/master/gradle.properties")
        use_released_versions = True

    if args.patch_level:
        print_info(f"Using patch level: {args.patch_level}")
        patch_level = args.patch_level

    if args.skip_build_distribution:
        print_info("Skipping ballerina-distribution build")
        build_distribution = False

    if args.publish_to_local_central:
        print_info("Pushing all the modules to local ballerina central repository")
        commands.append("-PpublishToLocalCentral=true")

    if args.additional_commands:
        commands = commands + list(filter(None, map(lambda command: command.strip(),
                                                    args.additional_commands.split(" "))))
        print_info(f'Using the command: "{" ".join(commands)}"')
    else:
        print_info(f'Using the command: "{" ".join(commands)}"')

    if args.continue_on_error:
        print_warn("Continuing the build even if a module build fails. However it will be stopped at the failing " +
                   "module level if '--update-stdlib-dependencies' is being used.")
        continue_on_error = True

    if args.up_to_module:
        print_info("Building up to the module: " + args.up_to_module)
        up_to_module = args.up_to_module

    if args.from_module:
        print_info("Building from the module: " + args.from_module)
        from_module = args.from_module

    if args.up_to_module:
        print_info("Building up to the module: " + args.up_to_module)
        up_to_module = args.up_to_module

    if args.test_module:
        print_info("Building from the module: " + args.from_module)
        test_module = args.test_module
        print_warn("'--test-module' flag will override '--up-to-module' & '--from-module' flags. It will skip the " +
                   "tests for dependency modules and dependent modules if '--update-stdlib-dependencies' flag " +
                   "is being used")

    if args.remove_after_build:
        print_info("Modules will be removed after the build")
        remove_after_build = True

    # Get released stdlib versions from ballerina-distribution/gradle.properties
    if use_released_versions:
        if patch_level:
            released_version_data_file_url = "https://raw.githubusercontent.com/ballerina-platform/" + \
                                             f"ballerina-distribution/{patch_level}/gradle.properties"
            read_released_stdlib_versions(released_version_data_file_url)
        else:
            print_error("Patch Level must be defined using '--patch-level' flag if you are using " +
                        "'--use-released-versions' flag")
            exit(1)

    read_stdlib_data(test_module)
    read_ignore_modules()

    start_build = False if from_module else True
    exit_code = 0
    for level in stdlib_modules_by_level:
        for module in stdlib_modules_by_level[level]:
            module_name = module['name']

            if from_module == module_name:
                start_build = True

            if module_name in build_ignore_modules:
                print_info(print_info("Skipping: " + module))
            elif start_build:
                clone_repository(module['name'])

                os.chdir(module_name)
                process_module(module, lang_version, use_released_versions, update_stdlib_dependencies,
                               keep_local_changes, downstream_branch)
                
                if not skip_tests and test_module and test_module != module_name:
                    build_commands = commands.copy()
                    build_command.append("-x")
                    build_command.append("test")
                    return_code = build_module(build_commands)
                else:
                    return_code = build_module(commands)
                
                if return_code != 0:
                    exit_code = return_code
                    if not continue_on_error:
                        exit(exit_code)
                os.chdir("..")

                if remove_after_build:
                    delete_module(module_name)

            if up_to_module == module_name:
                start_build = False

        if exit_code != 0:
            exit(exit_code)

    if build_distribution:
        clone_repository(BALLERINA_DIST_REPO_NAME)

        os.chdir(BALLERINA_DIST_REPO_NAME)
        process_module(BALLERINA_DIST_REPO_NAME, lang_version, use_released_versions, update_stdlib_dependencies,
                       keep_local_changes, downstream_branch)
        dist_build_commands = commands.copy()
        dist_build_commands.append("-x")
        dist_build_commands.append(":project-api-tests:test")
        return_code = build_module(dist_build_commands)
        if return_code != 0:
            exit_code = return_code
            exit(exit_code)
        os.chdir("..")


def process_module(module, lang_version, use_released_versions, update_stdlib_dependencies,
                   keep_local_changes, downstream_branch):
    global stdlib_versions

    module_name = module['name']
    module_version_key = module['version_key']

    print_block()
    print_info("Processing: " + module_name)

    module_branch = None
    if downstream_branch:
        module_branch = downstream_branch
        print_info(f"Using given downstream branch {module_branch}")
    if module_name in downstream_repo_branches:
        module_branch = downstream_repo_branches[module_name]
        print_info(f"Using defined branch {module_branch} in {TEST_IGNORE_MODULES_JSON}")
    elif use_released_versions:
        module_branch = f"v{released_stdlib_versions[module_version_key]}"
        print_info(f"Using released version tag {module_branch} in {released_version_data_file_url}")
    checkout_branch(module_branch, keep_local_changes)

    print_info("Branch: " + module_branch)
    print_block()

    module_version = get_version()
    print_info(f"Module {module_name} version: {module_version}")
    stdlib_versions[module_version_key] = module_version

    update_lang_version(lang_version)

    if update_stdlib_dependencies:
        update_stdlibs_version()
        remove_dependency_files()


def build_module(commands):
    process = subprocess.run(commands)

    return process.returncode


def remove_dependency_files():
    if Path("/ballerina/Dependencies.toml").is_file():
        print_info("Removing Dependencies.toml files in the ballerina directory")
        os.chdir("ballerina")
        subprocess.run("find", ".", "-name", "\"Dependencies.toml\"", "-delete")
        os.chdir("..")

    elif module_name == "module-ballerinai-transaction" and \
            Path(module_name + "/transaction-ballerina/Dependencies.toml").is_file():
        print_info("Removing Dependencies.toml files in the transaction-ballerina directory")
        os.chdir("transaction-ballerina")
        subprocess.run("find", ".", "-name", "\"Dependencies.toml\"", "-delete")
        os.chdir("..")

    if Path(module_name + "/ballerina-tests/Dependencies.toml").is_file():
        print_info("Removing Dependencies.toml files in the ballerina-tests directory")
        os.chdir("ballerina-tests")
        subprocess.run("find", ".", "-name", "\"Dependencies.toml\"", "-delete")
        os.chdir("..")


def delete_module(module_name):
    process = subprocess.run(["rm", "-rf", f"./{module_name}"])
    if process.returncode != 0:
        exit(process.returncode)


def update_lang_version(lang_version):
    config = ConfigObj(GRADLE_PROPERTIES)
    config['ballerinaLangVersion'] = lang_version
    config.write()
    print_info(f"Updating lang version: {config['ballerinaLangVersion']}")


def update_stdlibs_version():
    config = ConfigObj(GRADLE_PROPERTIES)
    properties = config.keys()
    for version_key in stdlib_versions:
        if version_key in properties:
            config[version_key] = stdlib_versions[version_key]
            print_info(f"Updating {version_key}: {stdlib_versions[version_key]}")
    config.write()


def clone_repository(module_name):
    print_info(f"Cloning Module: {module_name}")
    if module_name == "ballerina-lang":
        repo_path = f"https://www.github.com/{github_user}/{module_name}.git"
    else:
        repo_path = f"https://www.github.com/ballerina-platform/{module_name}.git"
    subprocess.run(["git", "clone", repo_path])


def get_version():
    config = ConfigObj(GRADLE_PROPERTIES)
    version = config['version']

    return version


def read_released_stdlib_versions(url):
    global released_stdlib_versions

    try:
        response = requests.get(url=url)
        if response.status_code == 200:
            response = requests.get(URL)
            open(RELEASED_VERSION_PROPERTIES, "wb").write(response.content)

            config = ConfigObj(RELEASED_VERSION_PROPERTIES)
            for property in config.keys():
                released_stdlib_versions[property] = config[property]

        else:
            print_error(f"Failed to access released version data from {url}")
            exit(1)
    except json.decoder.JSONDecodeError:
        print_error(f"Failed to access released version data from {url}")
        exit(1)


def checkout_branch(branch, keep_local_changes):
    try:
        return_code = subprocess.run(["git", "checkout", branch])
        if return_code != 0:
            print_warn(f"Failed to checkout branch {branch}. Default branch will be used.")
        if not keep_local_changes:
            subprocess.run(["git", "reset", "--hard", "origin/" + branch])
            subprocess.run(["git", "pull", "origin", branch])

    except Exception as e:
        print_warn("Failed to Sync the Default Branch: " + str(e))


def create_directory(directory_name):
    Path(directory_name).mkdir(parents=True, exist_ok=True)


def read_stdlib_data(test_module):
    global stdlib_modules_by_level

    try:
        response = requests.get(url=MODULE_LIST_JSON)
        if response.status_code == 200:
            stdlib_modules_data = json.loads(response.text)
            if test_module:
                read_data_for_module_testing(stdlib_modules_data, test_module)
            else:
                read_data_for_fbp(stdlib_modules_data)
        else:
            print_error(f"Failed to access standard library dependency data from {MODULE_LIST_JSON}")
            exit(1)
    except json.decoder.JSONDecodeError:
        print_error("Failed to load standard library dependency data")
        exit(1)


def read_data_for_fbp(stdlib_modules_data):
    global stdlib_modules_by_level

    for module in stdlib_modules_data['standard_library']:
        name = module['name']
        level = module['level']
        version_key = module['version_key']
        stdlib_modules_by_level[level] = stdlib_modules_by_level.get(level, []) + \
                                         [{"name": name, "version_key": version_key}]


def read_data_for_module_testing(stdlib_modules_data, test_module_name):
    global stdlib_modules_by_level

    standard_library_data = dict()
    module_dependencies = dict()
    for module in stdlib_modules_data['standard_library']:
        module_name = module['name']
        standard_library_data[module_name] = module
        dependents = module['dependents']
        for dependent in dependents:
            module_dependencies[dependent] = module_dependencies.get(dependent, []) + [module_name]

    if not test_module_name in standard_library_data.keys():
        print_error(f"Desired module {test_module_name} for testing was not found in {MODULE_LIST_JSON}")
        exit(1)
        
    module_list = {test_module_name}
    while module_list:
        current_module_name = module_list.pop()
        if current_module_name != test_module_name:
            level = standard_library_data[current_module_name]['level']
            version_key = standard_library_data[current_module_name]['version_key']
            if level in stdlib_modules_by_level.keys():
                repeated = False
                for module in stdlib_modules_by_level[level]:
                    if module["name"] == current_module_name:
                        repeated = True
                        break
                if not repeated:
                    stdlib_modules_by_level[level] = stdlib_modules_by_level.get(level, []) + \
                                                     [{"name": current_module_name, "version_key": version_key}]
            else:
                stdlib_modules_by_level[level] = [{"name": current_module_name, "version_key": version_key}]

        if current_module_name in module_dependencies.keys():
            dependencies = set(module_dependencies[current_module_name])
            module_list = module_list.union(dependencies)

    stdlib_levels = list(stdlib_modules_by_level.keys())
    stdlib_levels.sort()
    print_info("Following modules will be built with the pipeline")
    for level in stdlib_levels:
        print_info("Build Level: " + str(level))
        module_names = [module['name'] for module in stdlib_modules_by_level[level]]
        print_info("Modules: " + ", ".join(module_names))
    print_info("Testing Module: " + test_module_name)


def read_ignore_modules():
    global test_ignore_modules
    global build_ignore_modules
    global downstream_repo_branches

    try:
        file = open(TEST_IGNORE_MODULES_JSON)
        data = json.load(file)
        test_ignore_modules = data['master']['test-ignore-modules']
        build_ignore_modules = data['master']['build-ignore-modules']
        downstream_repo_branches = data['master']['downstream-repo-branches']

    except json.decoder.JSONDecodeError:
        print_error("Failed to load test ignore modules")
        exit(1)


def print_info(message):
    print(f'{Fore.GREEN}[INFO] {message}{Style.RESET_ALL}')


def print_error(message):
    print(f'{Fore.RED}[ERROR] {message}{Style.RESET_ALL}')
    sys.exit(1)


def print_warn(message):
    print(f'{Fore.YELLOW}[WARN] {message}{Style.RESET_ALL}')


def print_block():
    print()
    print("##############################################")
    print()


main()
