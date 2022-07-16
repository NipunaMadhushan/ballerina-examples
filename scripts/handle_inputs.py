import sys

repo_name = sys.argv[1]

branch = ''
if len(sys.argv) > 2:
    branch = sys.argv[2]

print(repo_name)
if branch == '':
    print('Branch not specified')
else:
    print(branch_name)
