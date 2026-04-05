import { useState, useEffect } from "react";

const CONSENT_KEY = "plano_cookie_consent";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem(CONSENT_KEY);
    if (!consent) setVisible(true);
  }, []);

  function accept() {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({ essential: true, analytics: true, date: new Date().toISOString() }));
    setVisible(false);
  }

  function essentialOnly() {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({ essential: true, analytics: false, date: new Date().toISOString() }));
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[100] p-4 bg-white border-t border-zinc-200 shadow-2xl">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex-1 text-sm text-zinc-600">
          <p className="font-medium text-zinc-900">Cookie Settings</p>
          <p className="mt-1">
            We use essential cookies to make PlanO work. We'd also like to use analytics cookies
            to understand how you use PlanO so we can improve it. No advertising cookies.{" "}
            <a href="/plano/legal/privacy" className="underline text-amber-700">Privacy Policy</a>
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={essentialOnly}
            className="px-4 py-2 text-sm border border-zinc-300 rounded-lg hover:bg-zinc-50 transition-colors"
          >
            Essential Only
          </button>
          <button
            onClick={accept}
            className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 transition-colors"
          >
            Accept All
          </button>
        </div>
      </div>
    </div>
  );
}
