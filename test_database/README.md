## Test database

Install NPM
```
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Load nvm into current shell session
export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh"

# Install Node.js (LTS version)
nvm install --lts

# Confirm it's installed
node -v
npm -v
```

Installer wrangler
```
npm install -g wrangler

# Confirm it's installed
wrangler --version
```

#### auth

Token
create api token on cloudflare
```
workers script: edit
D1: edit
Account Settings: read
```

test token is working using the command. Copy the token and export in shell:
```
export CLOUDFLARE_API_TOKEN=your_token_here
```

doing the following command should return your user id
```
wrangler whoami
```


#### Script dependencies and run

install python3
```
brew install python

# Verify installation
python3 --version
```

create virtual env
```
python3 -m venv venv
```

activate
```
source venv/bin/activate
```

install dependencies
```
pip3 install requests
```