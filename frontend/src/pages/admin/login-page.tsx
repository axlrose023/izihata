import { Link } from "react-router-dom";

import { LoginForm } from "@/modules/auth/components/login-form";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { Logo } from "@/shared/ui/logo";

export function AdminLoginPage() {
  useDocumentTitle("Вхід до панелі");
  return (
    <main className="login-page">
      <div className="login-page__brand">
        <Logo inverse />
        <div>
          <span>Внутрішній простір</span>
          <strong>IZI HATA</strong>
        </div>
        <Link to="/">← Повернутися до магазину</Link>
      </div>
      <div className="login-page__form">
        <LoginForm />
      </div>
    </main>
  );
}
