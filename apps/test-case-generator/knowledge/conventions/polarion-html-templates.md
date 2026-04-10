# Polarion HTML Templates

Fixed HTML templates for Polarion import. Use exactly as specified.

## Critical Formatting Rules

| Rule | Correct | Wrong |
|------|---------|-------|
| No space after `;` in styles | `font-size:11pt;font-family:Arial` | `font-size: 11pt; font-family: Arial` |
| Bold text | `<span style="font-weight:bold;">Text</span>` | `<b>Text</b>` |
| Escape `&&` | `&amp;&amp;` | `&&` |
| Line break | `<br>` | `\n` |
| Links | `<a href="URL" target="_top">Text</a>` | Plain URL |
| No `<code>` tags | Use plain text or `<pre>` blocks | `<code>text</code>` |

## Base Span Style

```
font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5;
```

## Setup Section Template

```html
<span style="font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5;"><span style="font-weight:bold;">Prerequisites:</span><br>• Item 1<br>• Item 2<br><br><span style="font-weight:bold;">Test Environment:</span><br>• Hub: cluster-name<br>• Console: https://console-url<br></span>
```

## Code Blocks (CLI/YAML)

```html
<pre style="font-family:Consolas,Monaco,monospace;font-size:10pt;background-color:#f5f5f5;padding:10px;border:1px solid #ccc;overflow-x:auto;">
# CLI commands or YAML here
oc get pods -n open-cluster-management
</pre>
```

## Test Steps Table Header

```html
<tbody><tr><th contenteditable="false" id="testStepKey:step" style="white-space:nowrap;height:12px;text-align:left;vertical-align:top;font-weight:bold;background-color:#F0F0F0;border:1px solid #CCCCCC;padding:5px;width:50%;">Step</th><th contenteditable="false" id="testStepKey:expectedResult" style="white-space:nowrap;height:12px;text-align:left;vertical-align:top;font-weight:bold;background-color:#F0F0F0;border:1px solid #CCCCCC;padding:5px;width:50%;">Expected Result</th></tr>
```

## Single Step Row Template

```html
<tr><td style="height:12px;text-align:left;vertical-align:top;line-height:18px;border:1px solid #CCCCCC;padding:5px;"><span style="font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5;"><span style="font-weight:bold;">Step {{NUM}}: {{TITLE}}</span><br><br>{{ACTIONS}}</span></td><td style="height:12px;text-align:left;vertical-align:top;line-height:18px;border:1px solid #CCCCCC;padding:5px;"><span style="font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5;">{{EXPECTED}}</span></td></tr>
```

Replace:
- `{{NUM}}` -- step number
- `{{TITLE}}` -- step title
- `{{ACTIONS}}` -- numbered actions separated by `<br>`
- `{{EXPECTED}}` -- expected results separated by `<br>` with `•` bullets
