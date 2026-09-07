import { Link } from "react-router-dom";

import { PageIntro } from "../components/PageIntro";

export function NotFoundPage() {
  return (
    <>
      <PageIntro eyebrow="Route not found" title="This project page does not exist">
        <p>The evidence console is available. Return to the APIx overview.</p>
      </PageIntro>
      <Link className="primary-link" to="/">Return to Overview</Link>
    </>
  );
}
