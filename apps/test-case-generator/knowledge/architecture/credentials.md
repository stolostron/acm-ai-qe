# Credentials Area Knowledge

## Overview

Credential management in ACM Console handles provider credentials for cluster creation and infrastructure access.

## Key Features
- Credential creation for various providers (AWS, Azure, GCP, vSphere, bare metal, etc.)
- Credential editing and rotation
- Credential usage tracking (which clusters use which credentials)

## Navigation Routes
- `credentials`: `/multicloud/credentials`
- `addCredentials`: `/multicloud/credentials/create`
- `editCredentials`: `/multicloud/credentials/edit/:namespace/:name`
- `viewCredentials`: `/multicloud/credentials/details/:namespace/:name`

## Testing Considerations
- Credentials contain secrets -- never display actual values in test steps
- Different provider types have different required fields
- Credential validation may require external API access
