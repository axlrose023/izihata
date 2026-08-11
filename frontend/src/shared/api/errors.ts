interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly details?: unknown,
    public readonly code: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function validationMessage(issues: ValidationIssue[]): string | null {
  const issue = issues.find((item) => typeof item.msg === "string");
  if (!issue?.msg) return null;

  const field = issue.loc?.at(-1);
  return typeof field === "string" ? `${field}: ${issue.msg}` : issue.msg;
}

export async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  const detail =
    payload && typeof payload === "object" && "detail" in payload
      ? (payload as { detail: unknown }).detail
      : null;
  const code =
    payload &&
    typeof payload === "object" &&
    "code" in payload &&
    typeof (payload as { code: unknown }).code === "string"
      ? (payload as { code: string }).code
      : null;
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? validationMessage(detail as ValidationIssue[])
        : null;

  return new ApiError(
    response.status,
    message ?? `Request failed with status ${response.status}`,
    payload,
    code,
  );
}

const localizedMessages: Record<string, string> = {
  conflict: "Дані вже були змінені. Оновіть сторінку та спробуйте ще раз.",
  delivery_provider_unavailable:
    "Автопідказки Нової пошти тимчасово недоступні. Введіть дані вручну.",
  duplicate_products: "У кошику є дубльований товар. Оновіть кошик.",
  internal_error: "На сервері сталася помилка. Спробуйте трохи пізніше.",
  method_not_allowed: "Ця дія не підтримується.",
  network_error: "Немає зв’язку із сервером. Перевірте інтернет і повторіть.",
  not_found: "Запитувані дані не знайдено.",
  products_unavailable:
    "Один або кілька товарів уже недоступні. Оновіть кошик.",
  promotion_invalid: "Промокод недійсний або термін його дії минув.",
  rate_limit_exceeded: "Забагато запитів. Зачекайте хвилину й повторіть.",
  request_timeout: "Сервер відповідає надто довго. Спробуйте ще раз.",
  service_unavailable: "Сервіс тимчасово недоступний. Спробуйте пізніше.",
  unauthorized: "Потрібна повторна авторизація.",
  validation_error: "Перевірте правильність заповнених даних.",
};

export function getUserErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.code && localizedMessages[error.code]) {
    return localizedMessages[error.code];
  }
  if (error.status === 401) return localizedMessages.unauthorized;
  if (error.status === 403) return "Недостатньо прав для цієї дії.";
  if (error.status === 404) return localizedMessages.not_found;
  if (error.status === 429) return localizedMessages.rate_limit_exceeded;
  if (error.status >= 500) return localizedMessages.internal_error;
  return fallback;
}
