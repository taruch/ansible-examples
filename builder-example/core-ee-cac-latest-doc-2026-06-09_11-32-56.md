## Documentation for the core-ee-cac:latest image 2026-06-09_11-32-56 :
<pre>
---------------------------------------------------------------
# 'podman images' bit for this doc:
aapp.state/core-ee-cac latest 029345256528 20 minutes ago 951 MB
---------------------------------------------------------------
# ansible --version output:
ansible [core 2.16.18]
  config file = None
  configured module search path = ['/runner/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/local/lib/python3.12/site-packages/ansible
  ansible collection location = /runner/.ansible/collections:/usr/share/ansible/collections
  executable location = /usr/local/bin/ansible
  python version = 3.12.13 (main, Apr 16 2026, 00:00:00) [GCC 11.5.0 20240719 (Red Hat 11.5.0-14)] (/usr/bin/python3.12)
  jinja version = 3.1.6
  libyaml = True
---------------------------------------------------------------
# ansible-galaxy collection list output:

# /usr/share/ansible/collections/ansible_collections
Collection                       Version     
-------------------------------- ------------
ansible.controller               4.8.0       
ansible.eda                      2.12.0      
ansible.hub                      1.0.6       
ansible.platform                 2.7.20260604
ansible.posix                    2.2.0       
community.general                13.0.1      
containers.podman                1.20.2      
infra.aap_configuration          4.6.0       
infra.aap_configuration_extended 4.7.0       
infra.aap_utilities              3.3.0       
infra.ah_configuration           2.1.0       
infra.ee_utilities               4.4.0       
kubernetes.core                  6.4.0       
redhat.openshift                 5.0.0       
---------------------------------------------------------------
# pip3 -V output:
pip 23.2.1 from /usr/lib/python3.12/site-packages/pip (python 3.12)
---------------------------------------------------------------
# pip3 list output:
Package            Version
------------------ -----------
aiobotocore        3.7.0
aiohappyeyeballs   2.6.1
aiohttp            3.13.5
aioitertools       0.13.0
aiokafka           0.14.0
aiosignal          1.4.0
ansible-compat     25.8.1
ansible-core       2.16.18
ansible-lint       25.8.2
ansible-runner     2.4.3
async-timeout      5.0.1
attrs              22.2.0
awxkit             24.6.1
azure-core         1.41.0
azure-servicebus   7.14.3
bcrypt             3.2.2
black              26.3.1
botocore           1.43.0
bracex             2.4
certifi            2038.12.31
cffi               2.0.0
charset-normalizer 3.3.0
click              8.1.7
cryptography       46.0.7
decorator          5.1.1
docutils           0.22.1
dpath              2.2.0
dumb-init          1.2.5
durationpy         0.10
filelock           3.13.1
frozenlist         1.8.0
gssapi             1.11.1
idna               3.4
importlib_metadata 9.0.0
isodate            0.7.2
Jinja2             3.1.6
jmespath           1.1.0
jsonpatch          1.33
jsonpointer        3.1.1
jsonschema         4.17.3
kafka-python-ng    2.2.3
krb5               0.9.0
kubernetes         36.0.2
lockfile           0.12.2
lxml               4.9.3
markdown-it-py     3.0.0
MarkupSafe         2.1.5
mdurl              0.1.2
multidict          6.7.1
mypy_extensions    1.0.0
ncclient           0.6.15
oauthlib           3.3.1
packaging          24.2
paramiko           3.4.0
pathspec           1.1.1
pexpect            4.9.0
pip                23.2.1
platformdirs       4.1.0
ply                3.11
propcache          0.4.1
psycopg            3.3.4
psycopg-binary     3.3.4
psycopg-pool       3.3.1
ptyprocess         0.7.0
pycparser          2.20
Pygments           2.17.2
pykerberos         1.2.4
PyNaCl             1.5.0
pyOpenSSL          26.0.0
pypsrp             0.8.1
pyrsistent         0.20.0
PySocks            1.7.1
pyspnego           0.10.2
python-daemon      3.1.2
python-dateutil    2.9.0.post0
pytokens           0.4.1
pytz               2026.2
pywinrm            0.4.3
PyYAML             6.0.3
referencing        0.37.0
requests           2.32.3
requests-credssp   2.0.0
requests_ntlm      1.2.0
requests-oauthlib  2.0.0
resolvelib         1.0.1
rich               13.7.0
rpds-py            0.24.0
ruamel.yaml        0.18.15
ruamel.yaml.clib   0.2.8
setuptools         68.2.2
six                1.17.0
subprocess-tee     0.4.1
toml               0.10.2
typing_extensions  4.15.0
urllib3            1.26.19
watchdog           6.0.0
wcmatch            8.5
websocket-client   1.9.0
wrapt              2.2.1
xmltodict          0.13.0
xxhash             3.7.0
yamllint           1.35.1
yarl               1.23.0
zipp               3.23.1
---------------------------------------------------------------
# env output:
HOSTNAME=74bb37eac2fd
PWD=/runner
PIP_BREAK_SYSTEM_PACKAGES=1
container=oci
HOME=/runner
OPENSHIFT_BUILD_COMMIT=dfc63b3976586ef23ad5a2724bf9bcfba14ccedc
TERM=xterm
OPENSHIFT_BUILD_NAMESPACE=aapp
OPENSHIFT_BUILD_NAME=core-ee-cac-10
SHLVL=0
OPENSHIFT_BUILD_SOURCE=https://SOM-CTO@dev.azure.com/SOM-CTO/PS-EVS-EnterpriseAnsible/_git/ee-build-core
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DESCRIPTION=Red Hat Ansible Automation Platform Minimal Execution Environment
_=/usr/bin/env
---------------------------------------------------------------
## Documentation for the core-ee-cac:latest image 2026-06-09_11-32-56 :
