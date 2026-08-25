import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import { getUserErrorMessage } from "@/shared/api/errors";

const loginSchema = z.object({
  email: z.string().trim().email("Вкажіть коректний email").max(254),
  password: z.string().min(1, "Вкажіть пароль").max(72),
});

const registerSchema = loginSchema.extend({
  full_name: z.string().trim().min(2, "Вкажіть ім’я").max(120),
  phone: z.string().trim().max(24).optional(),
  password: z
    .string()
    .min(8, "Пароль має містити щонайменше 8 символів")
    .max(72),
});

type LoginValues = z.infer<typeof loginSchema>;
type RegisterValues = z.infer<typeof registerSchema>;

export function CustomerAuthForm() {
  const [searchParams] = useSearchParams();
  const isRegister = searchParams.get("mode") === "register";
  const { login, register: registerCustomer } = useCustomerAuth();
  const navigate = useNavigate();
  const [requestError, setRequestError] = useState<string | null>(null);
  const loginForm = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
  });
  const registerForm = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
  });

  const submitLogin = loginForm.handleSubmit(async (values) => {
    setRequestError(null);
    try {
      await login(values.email, values.password);
      navigate("/account", { replace: true });
    } catch (error) {
      setRequestError(getUserErrorMessage(error, "Не вдалося увійти"));
    }
  });
  const submitRegister = registerForm.handleSubmit(async (values) => {
    setRequestError(null);
    try {
      await registerCustomer({
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        phone: values.phone || undefined,
      });
      navigate("/account", { replace: true });
    } catch (error) {
      setRequestError(getUserErrorMessage(error, "Не вдалося створити акаунт"));
    }
  });

  const form = isRegister ? registerForm : loginForm;
  return (
    <form
      className="customer-auth-form form-stack"
      onSubmit={isRegister ? submitRegister : submitLogin}
    >
      <span className="eyebrow">Особистий кабінет</span>
      <h1>{isRegister ? "Створити акаунт" : "Вхід до кабінету"}</h1>
      {isRegister ? (
        <label className="field">
          <span>Ім’я та прізвище</span>
          <input autoComplete="name" {...registerForm.register("full_name")} />
          {registerForm.formState.errors.full_name ? (
            <small>{registerForm.formState.errors.full_name.message}</small>
          ) : null}
        </label>
      ) : null}
      <label className="field">
        <span>Email</span>
        <input
          autoComplete="email"
          type="email"
          {...(isRegister
            ? registerForm.register("email")
            : loginForm.register("email"))}
        />
        {form.formState.errors.email ? (
          <small>{form.formState.errors.email.message}</small>
        ) : null}
      </label>
      {isRegister ? (
        <label className="field">
          <span>Телефон (необов’язково)</span>
          <input
            autoComplete="tel"
            inputMode="tel"
            {...registerForm.register("phone")}
          />
        </label>
      ) : null}
      <label className="field">
        <span>Пароль</span>
        <input
          autoComplete={isRegister ? "new-password" : "current-password"}
          type="password"
          {...(isRegister
            ? registerForm.register("password")
            : loginForm.register("password"))}
        />
        {form.formState.errors.password ? (
          <small>{form.formState.errors.password.message}</small>
        ) : null}
      </label>
      {requestError ? (
        <p className="form-error" role="alert">
          {requestError}
        </p>
      ) : null}
      <button
        className="button button--primary button--wide"
        disabled={form.formState.isSubmitting}
        type="submit"
      >
        {form.formState.isSubmitting
          ? "Зачекайте…"
          : isRegister
            ? "Створити акаунт"
            : "Увійти"}
      </button>
      <p className="customer-auth-form__switch">
        {isRegister ? "Вже маєте акаунт?" : "Ще не маєте акаунта?"}{" "}
        <Link
          to={isRegister ? "/account/login" : "/account/login?mode=register"}
        >
          {isRegister ? "Увійти" : "Зареєструватися"}
        </Link>
      </p>
    </form>
  );
}
