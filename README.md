\# SafeQ Cloud Manager



Web-based management interface for YSoft SafeQ Cloud print management system.



\## Features



\- 🔐 Entra ID (Azure AD) Single Sign-On

\- 👥 User management (view, create, edit)

\- 🔍 Advanced user search

\- 👨‍👩‍👧‍👦 Group management

\- 📊 Audit logging

\- 🔒 Role-based access control



\## Quick Start



\### Local Development



1\. Clone the repository

```bash

git clone https://github.com/yourusername/SafeQManager.git

cd SafeQManager

```



2\. Install dependencies

```bash

pip install -r requirements.txt

```



3\. Configure environment

```bash

cp .env.example .env

\# Edit .env with your values

```



4\. Run the application

```bash

streamlit run app/main.py

```



\### Streamlit Cloud Deployment



1\. Fork this repository

2\. Connect to Streamlit Cloud

3\. Add secrets in Settings → Secrets (use `.streamlit/secrets.toml.example` as template)

4\. Deploy!



\## Configuration



See `.env.example` for all available configuration options.



\### Required Secrets



\- `SERVER\_URL`: SafeQ Cloud server URL

\- `API\_KEY`: SafeQ API key

\- `TENANT\_ID`: Azure Tenant ID

\- `CLIENT\_ID`: Azure App Registration Client ID

\- `CLIENT\_SECRET`: Azure App Registration Secret



\## Documentation



\- \[Client Setup Guide](docs/client\_guide.md)

\- \[Deployment Guide](docs/deployment.md)



\## License



Proprietary - All rights reserved

