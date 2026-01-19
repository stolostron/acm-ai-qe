# JIRA API Script: Setup and Usage Guide for ACM Tickets

## 🚀 Overview

This guide explains how to set up your environment and use command-line tools to interact with Red Hat JIRA tickets via REST API and CLI, specifically focused on ACM (Advanced Cluster Management) tickets. The focus is on secure configuration and real-world usage patterns for Red Hat's JIRA instance.

***

## 📋 Prerequisites

1. **Red Hat JIRA Account**: Access to `https://issues.redhat.com` with appropriate permissions  
2. **Personal Access Token (PAT)**: Red Hat JIRA API token for secure authentication  
3. **Required Tools**: Both `curl` and `jq` must be installed, plus optionally `jira-cli` for enhanced functionality

***

## 🔑 Step 1: Generate Your Red Hat JIRA API Token

Red Hat uses Personal Access Tokens (PATs) for API authentication on their JIRA instance.

1. **Navigate** to the Red Hat JIRA Personal Access Tokens page:  
   `https://issues.redhat.com/secure/ViewProfile.jspa?selectedTab=com.atlassian.pats.pats-plugin:jira-user-personal-access-tokens`

2. Click **"Create token"**.

3. **Configure the token**:  
   - **Label**: Give it a descriptive name like `ACM-QE-API-Access` or `CLI-Script-Access`  
   - **Expires**: Set an appropriate expiration date (e.g., 90 days for security)  

4. **Copy the generated token immediately**. You will not be able to see it again. Store it securely.

***

## 🔧 Step 2: Configure Environment Variables

Use environment variables to store your credentials securely for Red Hat JIRA access.

```bash
# Red Hat JIRA instance (default for ACM tickets)
export JIRA_BASE_URL="https://issues.redhat.com"

# Your Red Hat email address
export JIRA_USERNAME="your.email@redhat.com"

# The Personal Access Token you just generated
export JIRA_API_TOKEN="your_generated_api_token_here"

# Optional: Additional JIRA CLI settings
export JIRA_AUTH_TYPE="bearer"
export JIRA_VERIFY_SSL="true"
export JIRA_TIMEOUT="30"
export JIRA_CACHE_DURATION="300"
```

💡 **Pro Tip**: Add these `export` commands to your shell's startup file (e.g., `~/.zshrc` or `~/.bashrc`) for persistence:

```bash
echo 'export JIRA_USERNAME="your.email@redhat.com"' >> ~/.zshrc
echo 'export JIRA_API_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

***

## 🛠️ Step 3: Install and Configure JIRA CLI (Optional but Recommended)

For enhanced functionality, install the JIRA CLI tool:

```bash
# Method 1: Go install (if Go is available)
go install github.com/ankitpokhrel/jira-cli@latest

# Method 2: Clone and build
cd /tmp
git clone https://github.com/ankitpokhrel/jira-cli.git
cd jira-cli
make install

# Verify installation
jira version
jq --version
```

**Initialize JIRA CLI**:
```bash
jira init
```
**Configuration settings:**
- Installation type: `Local`
- Jira server: `https://issues.redhat.com`
- Username: `your.email@redhat.com`
- Default project: `ACM` (or your preferred project)
- Default board: `None`

***

## ▶️ Step 4: Real-World ACM Ticket Usage Examples

Here are practical examples using actual ACM tickets from your workspace.

### Use Case 1: Get Basic Ticket Information
Check ticket status, summary, and key details for ACM tickets.

**Using curl (REST API):**
```bash
# Basic ticket info for ACM-22079
curl -s -u "$JIRA_USERNAME:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/2/issue/ACM-22079" | \
  jq '{key: .key, summary: .fields.summary, status: .fields.status.name, priority: .fields.priority.name}'
```

**Using JIRA CLI:**
```bash
# View ACM-20640 (RBAC UI Implementation)
jira issue view ACM-20640 --raw | jq '{key: .key, summary: .fields.summary, status: .fields.status.name}'

# View ACM-22079 with fix version
jira issue view ACM-22079 --raw | jq '{key: .key, fixVersion: (.fields.fixVersions[0].name // null), priority: .fields.priority.name}'
```

### Use Case 2: Analyze Linked Issues and Dependencies
Essential for understanding ACM ticket relationships and dependencies.

```bash
# Get linked issues for ACM-22080
jira issue view ACM-22080 --raw \
  | jq '.fields.issuelinks[] | {linkType: .type.name, key: (if .inwardIssue then .inwardIssue.key else .outwardIssue.key end), summary: (if .inwardIssue then .inwardIssue.fields.summary else .outwardIssue.fields.summary end), status: (if .inwardIssue then .inwardIssue.fields.status.name else .outwardIssue.fields.status.name end)}'

# Get subtasks for comprehensive tickets
jira issue view ACM-22079 --raw | jq '.fields.subtasks[] | {Subtask: .key, Summary: .fields.summary, Status: .fields.status.name}'
```

### Use Case 3: Extract Comments and Recent Updates
Monitor ticket progress and team communications.

```bash
# Get recent comments from ACM-20640
jira issue view ACM-20640 --raw \
  | jq '.fields.comment.comments[-5:][] | {author: .author.displayName, created: .created, comment: (.body | tostring)[0:200]}'

# Get all comments with author and date
jira issue view ACM-22079 --raw | jq '.fields.comment.comments[] | {Author: .author.displayName, Date: .created, Comment: .body}'
```

### Use Case 4: Comprehensive Ticket Analysis
Get all relevant information in one command - perfect for ACM ticket analysis.

```bash
# Complete ticket analysis for any ACM ticket
jira issue view ACM-22079 --raw | jq -r '
"🎫 " + .key + ": " + .fields.summary
+ "\n📊 STATUS: " + .fields.status.name
+ "\n⚠️ PRIORITY: " + .fields.priority.name
+ "\n🏷️ LABELS: " + (.fields.labels | join(", "))
+ "\n📅 UPDATED: " + .fields.updated
+ "\n🔧 FIX VERSION: " + ((.fields.fixVersions[0].name) // "None")
+ "\n👤 ASSIGNEE: " + ((.fields.assignee.displayName) // "Unassigned")
+ "\n\n📝 DESCRIPTION:\n" + (.fields.description // "No description")
+ "\n\n🔗 LINKED ISSUES:"
+ (if (.fields.issuelinks | length) > 0 then "\n" + (.fields.issuelinks | map("🔗 " + (if .inwardIssue then .inwardIssue.key + " - " + .inwardIssue.fields.summary else .outwardIssue.key + " - " + .outwardIssue.fields.summary end)) | join("\n")) else " None" end)
+ "\n\n📊 SUB-TASKS (" + (.fields.subtasks | length | tostring) + "):"
+ (if (.fields.subtasks | length) > 0 then "\n" + (.fields.subtasks | map("📌 " + .key + " [" + .fields.status.name + "] - " + .fields.summary) | join("\n")) else " None" end)'
```

### Use Case 5: Update Ticket Description from File
For comprehensive progress updates on ACM tickets.

```bash
# Update ACM-22620 description from a markdown file
./update-jira-ticket.sh --description-file progress-report.md

# Add a comment to ACM-22079
./update-jira-ticket.sh --comment "Test execution completed on mist10. Console: https://console-openshift-console.apps.mist10-0.qe.red-chesterfield.com"
```

### Use Case 6: Batch Analysis of Related ACM Tickets
Analyze multiple related tickets for comprehensive understanding.

```bash
# Analyze RBAC-related ACM tickets
RBAC_TICKETS=("ACM-20640" "ACM-20151" "ACM-22667" "ACM-22708" "ACM-22925")

for ticket in "${RBAC_TICKETS[@]}"; do
    echo "=== $ticket ==="
    jira issue view "$ticket" --raw | jq '{key: .key, summary: .fields.summary, status: .fields.status.name, priority: .fields.priority.name, fixVersion: (.fields.fixVersions[0].name // null)}'
    echo
done
```

### Use Case 7: Target Different Ticket Temporarily
Override the default ticket for one-off operations.

```bash
# Analyze ACM-23748 instead of default ticket
JIRA_TICKET_ID="ACM-23748" ./update-jira-ticket.sh --info

# Quick check of multiple tickets
for ticket in ACM-22079 ACM-22080 ACM-22081; do
    echo "--- $ticket ---"
    jira issue view "$ticket" --raw | jq '{status: .fields.status.name, updated: .fields.updated}'
done
```

***

## 🎯 Common ACM Ticket Patterns

Based on your workspace, here are common ACM ticket categories and their typical usage:

### **RBAC Implementation Tickets**
- **ACM-20640**: RBAC UI Implementation (Blocker priority)
- **ACM-20151**: ACM Fine Grained RBAC GA
- **ACM-22667**: Generate ClusterPermissions for Multiple Clusters in UI

### **MTV Integration Tickets**  
- **ACM-22348**: MTV addon integration (Critical, QE-Required)
- **ACM-21679**: Live migration testing
- **ACM-14983**: VNC console integration

### **Version-Specific Tickets**
- **ACM-22079**: ClusterCurator Digest Upgrades (ACM 2.15.0)
- **ACM-22080**: Related cluster management features
- **ACM-22457**: Component enhancements

***

## ⚠️ Troubleshooting

### **Authentication Issues**
```bash
# Error: 401 Unauthorized
# Solution: Check your credentials
echo "Username: $JIRA_USERNAME"
echo "Token set: $(if [[ -n "$JIRA_API_TOKEN" ]]; then echo "Yes"; else echo "No"; fi)"

# Test connection
curl -s -u "$JIRA_USERNAME:$JIRA_API_TOKEN" \
  "https://issues.redhat.com/rest/api/2/issue/ACM-22079" | jq .key
# Should return: "ACM-22079"
```

### **Permission Issues**
```bash
# Error: 403 Forbidden
# Solution: Ensure you have appropriate permissions
./update-jira-ticket.sh --info  # Test read access first

# Check project access
jira issue list -q 'project=ACM'
```

### **JIRA CLI Issues**
```bash
# CLI not found
which jira
jira version

# Authentication with CLI
jira issue list -q 'assignee=currentUser()'

# Multiple projects access
jira init  # Reconfigure if needed
```

### **Network and SSL Issues**
```bash
# Test Red Hat JIRA connectivity
curl -s "https://issues.redhat.com/rest/api/2/serverInfo" | jq .version

# SSL verification issues (if needed)
export JIRA_VERIFY_SSL="false"  # Use with caution
```

***

## 🛡️ Security Best Practices

- ✅ **Use Personal Access Tokens** - Safer than passwords, can be revoked individually
- ✅ **Set token expiration dates** - Regular rotation for security
- ✅ **Environment variables only** - Never commit tokens to version control
- ✅ **HTTPS everywhere** - All Red Hat JIRA communication is encrypted
- ✅ **Principle of least privilege** - Request only necessary permissions
- ⚠️ **Secure token storage** - Treat API tokens like passwords
- ⚠️ **Regular token rotation** - Update tokens before expiration

***

## 📚 Advanced Integration Examples

### **Integration with Test Generation**
```bash
# Extract ticket context for test generation
jira issue view ACM-22079 --raw > /tmp/ticket.json

# Use with claude-test-generator framework
python3 .claude/ai-services/jira_api_client.py ACM-22079
python3 .claude/ai-services/version_intelligence_service.py ACM-22079
```

### **Automated Reporting**
```bash
# Generate daily ACM ticket brief
for ticket in $(jira issue list -q 'project=ACM AND assignee=currentUser() AND status != Closed' --plain --columns KEY | tail -n +2); do
    echo "## $ticket"
    jira issue view "$ticket" --raw | jq -r '.fields.summary + " [" + .fields.status.name + "]"'
done
```

### **Batch Updates**
```bash
# Update multiple tickets with progress
TICKETS=("ACM-22079" "ACM-22080" "ACM-22081")
for ticket in "${TICKETS[@]}"; do
    JIRA_TICKET_ID="$ticket" ./update-jira-ticket.sh --comment "Automated test execution completed"
done
```

***

## 🔗 Resources and References

- **Red Hat JIRA**: https://issues.redhat.com
- **JIRA CLI Documentation**: https://github.com/ankitpokhrel/jira-cli
- **Red Hat API Policy**: https://spaces.redhat.com/display/OMEGA/API%2C+Script%2C+and+Bot+Policy
- **ACM Documentation**: https://access.redhat.com/documentation/en-us/red_hat_advanced_cluster_management_for_kubernetes

**Happy ACM ticket management!** 🎯
