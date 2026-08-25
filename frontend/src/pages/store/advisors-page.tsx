import {
  calculateAutonomy,
  calculateBreaker,
  calculateCable,
  calculateLedPowerSupply,
} from "@/modules/advisors/api/advisor-api";
import { AdvisorCalculator } from "@/modules/advisors/components/advisor-calculator";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function AdvisorsPage() {
  useDocumentTitle("Калькулятори та підбір");
  return (
    <div className="container advisors-page">
      <header className="advisors-page__header">
        <span className="eyebrow">Інструменти підбору</span>
        <h1>Розрахуйте базові параметри обладнання</h1>
        <p>
          Результати мають довідковий характер. Для складних або відповідальних
          об’єктів залучайте кваліфікованого електрика.
        </p>
      </header>
      <div className="advisors-page__grid">
        <AdvisorCalculator
          calculate={(values) =>
            calculateCable({
              current_a: values.current_a,
              length_m: values.length_m,
              conductor_material: values.conductor_material as
                "copper" | "aluminum",
            })
          }
          description="Оцінка перерізу кабелю за струмом, довжиною та матеріалом жили."
          fields={[
            {
              name: "current_a",
              label: "Струм, А",
              min: 0.1,
              initialValue: "16",
            },
            {
              name: "length_m",
              label: "Довжина лінії, м",
              min: 0.1,
              initialValue: "20",
            },
            {
              name: "conductor_material",
              label: "Матеріал жили",
              type: "select",
              initialValue: "copper",
              options: [
                { value: "copper", label: "Мідь" },
                { value: "aluminum", label: "Алюміній" },
              ],
            },
          ]}
          renderMetrics={(result) => [
            { label: "Розрахунковий струм", value: `${result.current_a} А` },
            {
              label: "Рекомендований переріз",
              value: `${result.recommended_cross_section_mm2} мм²`,
            },
          ]}
          title="Підбір перерізу кабелю"
        />
        <AdvisorCalculator
          calculate={(values) =>
            calculateBreaker({
              current_a: values.current_a,
              load_type: values.load_type as "resistive" | "lighting" | "motor",
              wiring_current_limit_a:
                values.wiring_current_limit_a || undefined,
            })
          }
          description="Рекомендація автомата та характеристик захисту для базового навантаження."
          fields={[
            {
              name: "current_a",
              label: "Струм навантаження, А",
              min: 0.1,
              initialValue: "16",
            },
            {
              name: "load_type",
              label: "Тип навантаження",
              type: "select",
              initialValue: "resistive",
              options: [
                { value: "resistive", label: "Резистивне" },
                { value: "lighting", label: "Освітлення" },
                { value: "motor", label: "Двигун" },
              ],
            },
            {
              name: "wiring_current_limit_a",
              label: "Допустимий струм проводки, А",
              min: 0.1,
              initialValue: "",
              required: false,
            },
          ]}
          renderMetrics={(result) => [
            { label: "Розрахунковий струм", value: `${result.current_a} А` },
            {
              label: "Номінал автомата",
              value: result.recommended_nominal_a
                ? `${result.recommended_nominal_a} А`
                : "Потрібна консультація",
            },
            { label: "Характеристика", value: result.recommended_curve },
          ]}
          title="Підбір автоматичного вимикача"
        />
        <AdvisorCalculator
          calculate={(values) =>
            calculateLedPowerSupply({
              length_m: values.length_m,
              watts_per_meter: values.watts_per_meter,
              reserve_percent: values.reserve_percent,
            })
          }
          description="Оцініть потужність блока живлення для LED-стрічки з необхідним запасом."
          fields={[
            {
              name: "length_m",
              label: "Довжина стрічки, м",
              min: 0.1,
              initialValue: "5",
            },
            {
              name: "watts_per_meter",
              label: "Потужність на метр, Вт",
              min: 0.1,
              initialValue: "14.4",
            },
            {
              name: "reserve_percent",
              label: "Запас потужності, %",
              min: 10,
              initialValue: "20",
            },
          ]}
          renderMetrics={(result) => [
            { label: "Навантаження", value: `${result.load_w} Вт` },
            {
              label: "Рекомендована потужність",
              value: `${result.recommended_power_w} Вт`,
            },
          ]}
          title="Блок живлення для LED-стрічки"
        />
        <AdvisorCalculator
          calculate={(values) =>
            calculateAutonomy({
              load_w: values.load_w,
              hours: values.hours,
              battery_voltage_v: values.battery_voltage_v,
            })
          }
          description="Базовий розрахунок резервного живлення: акумулятор та інвертор."
          fields={[
            {
              name: "load_w",
              label: "Навантаження, Вт",
              min: 1,
              initialValue: "500",
            },
            {
              name: "hours",
              label: "Час автономності, год",
              min: 0.1,
              initialValue: "4",
            },
            {
              name: "battery_voltage_v",
              label: "Напруга АКБ, В",
              min: 1,
              initialValue: "24",
            },
          ]}
          renderMetrics={(result) => [
            {
              label: "Потрібна енергія",
              value: `${result.required_energy_wh} Вт·год`,
            },
            {
              label: "Ємність АКБ",
              value: `${result.recommended_battery_capacity_ah} А·год`,
            },
            {
              label: "Потужність інвертора",
              value: `${result.recommended_inverter_power_w} Вт`,
            },
          ]}
          title="Резервне живлення"
        />
      </div>
    </div>
  );
}
