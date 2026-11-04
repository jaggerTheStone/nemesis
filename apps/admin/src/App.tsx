import { t } from "./i18n/index.js";

export function App() {
  return (
    <main>
      <h1>
        {t("app.name")} · {t("admin.title")}
      </h1>
      <p>{t("admin.placeholder")}</p>
    </main>
  );
}
