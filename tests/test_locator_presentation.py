import subprocess
from pathlib import Path


APP_JS = Path(__file__).parents[1] / "src" / "cpf_fcv_reviewer" / "static" / "app.js"


def test_browser_locator_deduplicates_only_matching_page_element():
    script = r"""
      const fs = require("fs");
      const source = fs.readFileSync(process.argv[1], "utf8");
      const start = source.indexOf("function locatorLabel(locator) {");
      const end = source.indexOf("function evidenceTypeLabel", start);
      eval(source.slice(start, end));
      const duplicate = locatorLabel({
        document_title: "CPF.pdf", page: 5, heading: "Results", element: "page 5",
      });
      const distinct = locatorLabel({
        document_title: "CPF.pdf", page: 5, heading: "Results", element: "paragraph 12",
      });
      if (duplicate !== "CPF.pdf | page 5 | Results") throw Error(duplicate);
      if (distinct !== "CPF.pdf | page 5 | Results | paragraph 12") throw Error(distinct);
    """

    completed = subprocess.run(
        ["node", "-e", script, str(APP_JS)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
