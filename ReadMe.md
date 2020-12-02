### OSX

```bash
sudo port install python38 py38-setuptools py38-setuptools py38-psycopg2 openssl

# Instructions For Variables
# https://stackoverflow.com/a/65072442/6828099
# https://stackoverflow.com/a/60748789/6828099

export PATH=/opt/local/lib/postgresql13/bin/:$PATH
export LDFLAGS="-L/opt/local/lib"
export CPPFLAGS="-I/opt/local/include"

pi3 install -r requirements.txt
```