import { useEffect, useRef, type ReactNode } from "react";

type PageIntroProps = {
  eyebrow: string;
  title: string;
  children: ReactNode;
};

export function PageIntro({ eyebrow, title, children }: PageIntroProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, [title]);

  return (
    <header className="page-intro">
      <p className="page-code"><span aria-hidden="true">//</span> {eyebrow}</p>
      <h1 ref={headingRef} tabIndex={-1}>{title}</h1>
      <div className="page-summary">{children}</div>
    </header>
  );
}
