import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle, LockKeyhole } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "@/modules/auth/auth-provider";
import { ApiError, getUserErrorMessage } from "@/shared/api/errors";

const schema = z.object({
  username: z.string().trim().min(1, "Вкажіть логін").max(64),
  password: z.string().min(1, "Вкажіть пароль").max(72),
});

type Values = z.infer<typeof schema>;

export function LoginForm() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const [requestError, setRequestError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (status === "authenticated") navigate("/admin", { replace: true });
  }, [navigate, status]);

  const submit = handleSubmit(async (values) => {
    setRequestError(null);
    try {
      await login(values.username, values.password);
      navigate("/admin", { replace: true });
    } catch (error) {
      setRequestError(
        error instanceof ApiError && error.status === 401
          ? "Невірний логін або пароль"
          : getUserErrorMessage(error, "Не вдалося увійти"),
      );
    }
  });

  return (
    <form className="login-form" onSubmit={submit}>
      <div className="login-form__icon">
        <LockKeyhole />
      </div>
      <div>
        <span className="eyebrow">Адміністрування</span>
        <h1>Вхід до панелі</h1>
      </div>
      <label className="field">
        <span>Логін</span>
        <input autoComplete="username" autoFocus {...register("username")} />
        {errors.username ? <small>{errors.username.message}</small> : null}
      </label>
      <label className="field">
        <span>Пароль</span>
        <input
          autoComplete="current-password"
          type="password"
          {...register("password")}
        />
        {errors.password ? <small>{errors.password.message}</small> : null}
      </label>
      {requestError ? (
        <p className="form-error" role="alert">
          {requestError}
        </p>
      ) : null}
      <button
        className="button button--primary button--wide"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? <LoaderCircle className="spin" size={18} /> : null}
        {isSubmitting ? "Входимо…" : "Увійти"}
      </button>
    </form>
  );
}
