# Code Analysis Rules

## Mandatory Rules

1. **Read full source of primary target file** via acm-source MCP `get_component_source()`. The primary file is the one named in the JIRA story or the file with the most significant behavioral changes. Do NOT rely solely on the diff for behavioral conclusions.

2. **Distinguish test files from production code.** Files ending in `.test.tsx` or `.test.ts` contain mock data (jest.mock, fixture objects, test renderers). Mock data does NOT represent what the UI renders. Label claims derived from test files as "FROM TEST MOCK DATA -- verify against production code."

3. **Multi-story PRs.** When a PR references multiple JIRA stories, identify which files belong to which story. Tag each changed file with its story. Focus analysis on the target story's files. Note other story changes separately.

4. **Cross-reference with area knowledge.** If `acm-knowledge-base/references/architecture/<area>.md` contains field order, filtering behavior, or component structure information, verify that your analysis is consistent. If you find a conflict between your diff analysis and the knowledge file, flag it explicitly.

5. **MCP source is authoritative.** If the MCP source (via `get_component_source`) differs from the PR diff (different function implementation, different import path), trust the MCP source -- it reflects the actual merged/release code. The PR diff may show a draft version that was changed before merge.

6. **Filter function extraction.** When the diff introduces or modifies a filtering function, call `get_component_source()` on the utility file that defines the function. Extract the EXACT conditions (string comparisons, `startsWith` calls, regex patterns). Do NOT paraphrase or summarize -- extract the literal code.

7. **Verify UI strings.** For any new UI labels found in the diff, call `search_translations()` to get the exact translation key and English text. Test cases must use the exact strings users see.
