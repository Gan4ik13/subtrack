"""Генератор SEO-кластера «Как отменить подписку …».

Собирает статические страницы frontend/cancel/<slug>.html из данных SERVICES
ниже, hub-страницу frontend/cancel/index.html и sitemap.xml.
Перегенерировать после правок данных: python scripts/generate_cancel_pages.py
"""

import datetime
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "frontend", "cancel")

DOMAIN = "https://subping.ru"

METRIKA = """<!-- Yandex.Metrika counter -->
<script type="text/javascript">
    (function(m,e,t,r,i,k,a){
        m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
        m[i].l=1*new Date();
        for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
    })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=111766811', 'ym');
    ym(111766811, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:"dataLayer", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/111766811" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
<!-- /Yandex.Metrika counter -->"""

SERVICES = [
    {
        "slug": "yandex-plus",
        "name": "Яндекс Плюс",
        "price": "от 299 ₽/мес",
        "lead": "Яндекс Плюс объединяет Кинопоиск, Яндекс Музыку, Плюс с Маркетом и другие сервисы. Подписка продлевается автоматически — отключить автопродление можно в любой момент.",
        "web_steps": [
            "Зайдите на id.yandex.ru под своим аккаунтом.",
            "Откройте раздел «Подписки» (или «Платежи и подписки»).",
            "Выберите «Яндекс Плюс» → «Управление». ",
            "Нажмите «Отключить подписку» и подтвердите действие.",
        ],
        "app_steps": [
            "Откройте приложение Яндекса или Кинопоиска.",
            "Профиль → «Плюс» (или «Подписка»).",
            "«Управление подпиской» → «Отключить».",
        ],
        "after": "Подписка останется активной до конца уже оплаченного периода. Отмена не возвращает деньги за текущий месяц, но останавливает следующие списания.",
        "tips": "Если Плюс оформлен как часть семейной подписки, отключать её должен владелец. Проверьте также отдельные списания за Яндекс Музыку и Кинопоиск — после отмены Плюса они не отключатся автоматически, если оформлены раздельно.",
    },
    {
        "slug": "kinopoisk",
        "name": "Кинопоиск",
        "price": "от 299 ₽/мес",
        "lead": "Подписка Кинопоиск продлевается автоматически каждый месяц. Отключить автопродление можно с сайта или из приложения за пару минут.",
        "web_steps": [
            "Зайдите на kinopoisk.ru и войдите в аккаунт.",
            "Нажмите на аватар → «Подписка».",
            "В блоке управления подпиской выберите «Отключить автопродление».",
            "Подтвердите отмену — на экране появится дата окончания доступа.",
        ],
        "app_steps": [
            "В приложении Кинопоиск откройте профиль.",
            "«Подписка» → «Управление». ",
            "«Отключить автопродление» → подтвердите.",
        ],
        "after": "Доступ к фильмам сохранится до конца оплаченного периода. Повторно подключить подписку можно в любой момент.",
        "tips": "Если подписка оформлена через Яндекс Плюс, отменять её нужно в разделе подписок Яндекса (id.yandex.ru), а не на Кинопоиске.",
    },
    {
        "slug": "ivi",
        "name": "ИВИ",
        "price": "от 299 ₽/мес",
        "lead": "ИВИ списывает оплату автоматически. Автопродление отключается в личном кабинете на сайте или в приложении.",
        "web_steps": [
            "Зайдите на ivi.ru и войдите в аккаунт.",
            "Перейдите в профиль → «Подписка». ",
            "Нажмите «Отключить автопродление» и подтвердите.",
        ],
        "app_steps": [
            "В приложении ИВИ откройте «Мой ИВИ» → профиль.",
            "«Подписка» → «Управление» → «Отключить автопродление».",
        ],
        "after": "Просмотр доступен до конца уже оплаченного периода, дальше списаний не будет.",
        "tips": "При оплате через мобильных операторов или Smart TV отмена может требовать звонка оператору — проверьте, какой способ оплаты указан в разделе «Подписка».",
    },
    {
        "slug": "okko",
        "name": "Okko",
        "price": "от 299 ₽/мес",
        "lead": "Онлайн-кинотеатр Okko автоматически продлевает подписку. Отключить автопродление можно в личном кабинете.",
        "web_steps": [
            "Зайдите на okko.tv и войдите в аккаунт.",
            "Откройте личный кабинет → «Подписка». ",
            "Нажмите «Отключить автопродление» и подтвердите отмену.",
        ],
        "app_steps": None,
        "after": "Подписка действует до конца оплаченного периода, после чего списания прекратятся.",
        "tips": "Если подписка оформлена через телевизор или оператора (Ростелеком, ТТК), отменяйте в личном кабинете оператора.",
    },
    {
        "slug": "telegram-premium",
        "name": "Telegram Premium",
        "price": "от 349 ₽/мес",
        "lead": "Telegram Premium продлевается автоматически. Где отменять — зависит от того, где вы его оформляли: в приложении Telegram или через App Store/Google Play.",
        "web_steps": [
            "Откройте Telegram → Настройки → Telegram Premium.",
            "«Управление подпиской» (откроется окно оплаты).",
            "Выберите «Отменить подписку» и подтвердите.",
        ],
        "app_steps": [
            "Android: если оформляли через Google Play — Play Market → профиль → «Платежи и подписки» → Telegram → «Отменить подписку».",
            "iPhone: Настройки iOS → ваше имя → «Подписки» → Telegram → «Отменить подписку».",
        ],
        "after": "Преимущества Premium сохранятся до конца оплаченного периода. Отмена через магазин приложений может занять несколько часов, чтобы отобразиться в Telegram.",
        "tips": "Если кнопки «Управление подпиской» нет — значит, оплата идёт через магазин приложений, и отменять нужно именно там. Проверьте список подписок в App Store или Google Play.",
    },
    {
        "slug": "spotify",
        "name": "Spotify",
        "price": "от 199 ₽/мес",
        "lead": "Spotify продлевает подписку автоматически. Отмена делается на сайте сервиса в настройках аккаунта.",
        "web_steps": [
            "Зайдите на account.spotify.com и войдите в аккаунт.",
            "Откройте раздел «План» (Your plan).",
            "Нажмите «Изменить или отменить» → «Отменить подписку».",
            "Подтвердите отмену в пошаговом диалоге.",
        ],
        "app_steps": None,
        "after": "Аккаунт переходит на бесплатный тариф после окончания оплаченного периода. Плейлисты сохраняются.",
        "tips": "Если оплата проходит через партнёров (например, через подписку оператора), отменяйте у партнёра.",
    },
    {
        "slug": "yandex-music",
        "name": "Яндекс Музыка",
        "price": "от 169 ₽/мес",
        "lead": "Отдельная подписка Яндекс Музыки продлевается автоматически. Часто она идёт в комплекте с Яндекс Плюсом — проверьте, какой вариант у вас.",
        "web_steps": [
            "Зайдите на id.yandex.ru под своим аккаунтом.",
            "Откройте «Подписки».",
            "Выберите «Яндекс Музыка» → «Управление» → «Отключить подписку».",
        ],
        "app_steps": [
            "В приложении Яндекс Музыки: Профиль → «Подписка».",
            "«Управление» → «Отключить».",
        ],
        "after": "Музыка будет доступна до конца оплаченного периода. Если у вас Яндекс Плюс, музыка отключится вместе с ним.",
        "tips": "Выгоднее сравнить: отдельная подписка на музыку или Плюс, который включает её вместе с Кинопоиском.",
    },
    {
        "slug": "apple-music",
        "name": "Apple Music",
        "price": "от 169 ₽/мес",
        "lead": "Apple Music привязана к Apple ID и отменяется в настройках подписок Apple на устройстве или в App Store.",
        "web_steps": [
            "На iPhone/iPad: Настройки → ваше имя → «Подписки».",
            "Выберите Apple Music → «Отменить подписку».",
            "С компьютера Mac: App Store → профиль → «Параметры учётной записи» → «Управление» → «Изменить» → отмена.",
        ],
        "app_steps": None,
        "after": "Сервис работает до конца оплаченного периода. Библиотека и плейлисты сохраняются на 30 дней, потом удаляются.",
        "tips": "Если кнопки отмены нет, проверьте, не входит ли подписка в семейный или партнёрский тариф — тогда управляет её владелец.",
    },
    {
        "slug": "youtube-premium",
        "name": "YouTube Premium",
        "price": "от 199 ₽/мес",
        "lead": "YouTube Premium автоматически списывает оплату каждый месяц. Отменяется на странице платных подписок Google.",
        "web_steps": [
            "Зайдите на youtube.com/paid_memberships под своим аккаунтом Google.",
            "Нажмите «Управление» напротив YouTube Premium.",
            "Выберите «Отменить подписку» и укажите причину (можно пропустить).",
        ],
        "app_steps": [
            "В приложении YouTube: Профиль → «Покупки и платежи».",
            "Выберите подписку → «Отменить подписку».",
        ],
        "after": "Premium-доступ сохранится до конца оплаченного периода. Если подписка оформлена через App Store — отменяйте в настройках iOS (имя → «Подписки»).",
        "tips": "Проверьте также семейную подписку YouTube Premium и YouTube Music — они оплачиваются отдельными списаниями.",
    },
    {
        "slug": "icloud",
        "name": "iCloud+",
        "price": "от 59 ₽/мес",
        "lead": "iCloud+ — платное расширение хранилища Apple. Полностью «отменить» его нельзя: можно только перейти на бесплатный тариф 5 ГБ.",
        "web_steps": [
            "iPhone/iPad: Настройки → ваше имя → iCloud → «Управление хранилищем аккаунта».",
            "«Сменить тарифный план». ",
            "Выберите бесплатный тариф 5 ГБ и подтвердите.",
        ],
        "app_steps": None,
        "after": "Следующее списание не произойдёт. Если данных больше 5 ГБ, новые файлы перестанут синхронизироваться — сначала скачайте важное.",
        "tips": "Перед понижением тарифа сохраните фото и документы локально: при превышении 5 ГБ синхронизация новых данных остановится.",
    },
    {
        "slug": "google-one",
        "name": "Google One",
        "price": "от 99 ₽/мес",
        "lead": "Google One расширяет хранилище Google (Диск, Gmail, Фото). Подписку можно отменить в любой момент — доступ сохранится до конца периода.",
        "web_steps": [
            "Зайдите на one.google.com под своим аккаунтом Google.",
            "«Настройки» → «Изменить тарифный план».",
            "Выберите «Отменить подписку» (или бесплатный тариф) и подтвердите.",
        ],
        "app_steps": [
            "В приложении Google One: Меню → «Настройки» → «Изменить тарифный план» → отмена.",
        ],
        "after": "Хранилище вернётся к бесплатным 15 ГБ после окончания оплаченного периода. Превышение лимита блокирует новую загрузку файлов и письма в Gmail.",
        "tips": "Если подписка оформлена через Google Play, отмена доступна также в Play Market → «Платежи и подписки».",
    },
    {
        "slug": "yandex-disk",
        "name": "Яндекс Диск (Про)",
        "price": "от 99 ₽/мес",
        "lead": "Платный тариф Яндекс Диска продлевается автоматически. Отключить автопродление можно на странице подписок Яндекса.",
        "web_steps": [
            "Зайдите на id.yandex.ru.",
            "Откройте «Подписки».",
            "Выберите «Яндекс Диск» → «Управление» → «Отключить подписку».",
        ],
        "app_steps": [
            "В приложении Диска: Профиль → «Про-тариф» → «Управление подпиской».",
        ],
        "after": "Место на бесплатном тарифе — 5 ГБ. Если хранилище переполнено, загрузка новых файлов будет ограничена.",
        "tips": "Перед отменой скачайте файлы, объём которых превышает бесплатный лимит.",
    },
    {
        "slug": "ozon-premium",
        "name": "Ozon Premium",
        "price": "от 99 ₽/мес",
        "lead": "Ozon Premium даёт скидки и быструю доставку, но продлевается автоматически. Отключить его можно в личном кабинете.",
        "web_steps": [
            "Зайдите на ozon.ru и войдите в аккаунт.",
            "Профиль → «Ozon Premium». ",
            "«Управление подпиской» → «Отключить автопродление».",
        ],
        "app_steps": [
            "В приложении Ozon: Профиль → Ozon Premium → «Управление» → «Отключить».",
        ],
        "after": "Привилегии Premium действуют до конца оплаченного периода. Следующее списание не выполнится.",
        "tips": "Если подписка оформлена недавно и вы ей не пользовались, обратитесь в поддержку Ozon — в отдельных случаях возможен возврат.",
    },
    {
        "slug": "sberprime",
        "name": "СберПрайм",
        "price": "от 199 ₽/мес",
        "lead": "СберПрайм объединяет сервисы Сбербанка (СберЗвук, Okko, Самокат и др.) и продлевается автоматически. Отмена — в приложении СберБанк Онлайн или на сайте СберПрайма.",
        "web_steps": [
            "Откройте СберБанк Онлайн → Профиль → «СберПрайм».",
            "«Управление подпиской» → «Отключить». ",
            "Подтвердите отмену.",
        ],
        "app_steps": None,
        "after": "Подписка останется активной до конца оплаченного периода. Отдельные сервисы-партнёры могут требовать отдельной отмены.",
        "tips": "Отменить подписку можно также на сайте sberprime.sber.ru в разделе личного кабинета.",
    },
    {
        "slug": "vk-music",
        "name": "VK Музыка",
        "price": "от 169 ₽/мес",
        "lead": "Подписка VK Музыка (ранее BOOM) списывается автоматически. Отключить её можно в настройках платежей VK.",
        "web_steps": [
            "Зайдите на vk.com и войдите в аккаунт.",
            "Настройки → «Платежи и подписки».",
            "Выберите подписку VK Музыка → «Отключить автопродление».",
        ],
        "app_steps": [
            "В приложении VK Музыки: Меню → «Подписка» → «Управление» → «Отключить».",
        ],
        "after": "Музыка доступна до конца оплаченного периода, затем аккаунт перейдёт на бесплатный режим с ограничениями.",
        "tips": "Если подписка оформлена через мобильного оператора, отменять её нужно у оператора.",
    },
    {
        "slug": "netflix",
        "name": "Netflix",
        "price": "от 299 ₽/мес",
        "lead": "Netflix продлевается автоматически. Отменить подписку можно в настройках аккаунта на сайте.",
        "web_steps": [
            "Зайдите на netflix.com и войдите в аккаунт.",
            "Профиль → «Аккаунт» (Account).",
            "«Отменить членство» (Cancel Membership) → подтвердите.",
        ],
        "app_steps": None,
        "after": "Просмотр доступен до конца оплаченного периода. Профили и списки сохраняются 10 месяцев после отмены.",
        "tips": "Если оплата проходит через партнёра (оператор, пакет сервисов), кнопка отмены ведёт к инструкции партнёра.",
    },
    {
        "slug": "microsoft-365",
        "name": "Microsoft 365",
        "price": "от 699 ₽/мес",
        "lead": "Подписка Microsoft 365 (Office + OneDrive) продлевается автоматически. Отмена — в разделе «Службы и подписки» учётной записи Microsoft.",
        "web_steps": [
            "Зайдите на account.microsoft.com/services под своей учётной записью.",
            "Найдите Microsoft 365 → «Управление». ",
            "«Отключить периодические платежи» или «Отменить подписку» → подтвердите.",
        ],
        "app_steps": None,
        "after": "После окончания оплаченного периода приложения Office переходят в режим с ограниченной функциональностью, объём OneDrive сокращается до 5 ГБ.",
        "tips": "Если подписка оформлена через App Store/Google Play, отменяйте её в настройках магазина приложений.",
    },
    {
        "slug": "chatgpt-plus",
        "name": "ChatGPT Plus",
        "price": "от 1 900 ₽/мес",
        "lead": "ChatGPT Plus списывается каждый месяц автоматически. Отменяется в настройках аккаунта ChatGPT.",
        "web_steps": [
            "Зайдите на chatgpt.com и войдите в аккаунт.",
            "Профиль → «Мой план» (My plan).",
            "«Управление подпиской» → «Отменить подписку».",
        ],
        "app_steps": [
            "Если оформляли через iPhone: Настройки iOS → ваше имя → «Подписки» → ChatGPT → «Отменить».",
            "Если через Android — в Google Play → «Платежи и подписки».",
        ],
        "after": "Plus работает до конца оплаченного периода, затем аккаунт перейдёт на бесплатную версию.",
        "tips": "Сумма списывается в валюте региона вашей карты — при отмене и повторном оформлении тариф может смениться.",
    },
    {
        "slug": "wb-premium",
        "name": "WB Premium (Вайлдберриз)",
        "price": "от 99 ₽/мес",
        "lead": "WB Premium даёт скидку и бонусы на маркетплейсе и продлевается автоматически. Отключить можно в профиле покупателя.",
        "web_steps": [
            "Зайдите на wildberries.ru и войдите в аккаунт.",
            "Профиль → «WB Premium». ",
            "«Управление подпиской» → «Отключить автопродление».",
        ],
        "app_steps": [
            "В приложении WB: Профиль → «WB Premium» → «Управление» → «Отключить».",
        ],
        "after": "Скидки Premium действуют до конца оплаченного периода. Новые списания производиться не будут.",
        "tips": "Оформляйте подписку только если средний чек покупок окупает её стоимость — иначе это лишняя статья расходов.",
    },
    {
        "slug": "litres",
        "name": "ЛитРес (абонемент)",
        "price": "от 299 ₽/мес",
        "lead": "Абонемент ЛитРес открывает доступ к каталогу книг и продлевается автоматически. Отключить автопродление можно в личном кабинете.",
        "web_steps": [
            "Зайдите на litres.ru и войдите в аккаунт.",
            "Профиль → «Абонемент».",
            "«Управление» → «Отключить автопродление».",
        ],
        "app_steps": [
            "В приложении: Профиль → «Абонемент» → «Отключить автопродление».",
        ],
        "after": "Чтение доступно до конца оплаченного периода. Купленные отдельно книги остаются у вас навсегда.",
        "tips": "Книги, купленные не по абонементу, отмене не подлежат — отменяется только само автопродление абонемента.",
    },
]

STORE_NOTE = (
    "Если подписка была оформлена через App Store или Google Play, отменять её нужно "
    "именно там: iOS — Настройки → ваше имя → «Подписки»; Android — Play Market → "
    "профиль → «Платежи и подписки». Отмена на сайте сервиса в этом случае не остановит списания."
)


def esc(s):
    return html.escape(s, quote=True)


def page_html(s):
    title = f"Как отменить подписку {s['name']}: пошаговая инструкция"
    description = (
        f"Как отменить подписку {s['name']} ({s['price']}) и отключить автопродление. "
        f"Пошаговая инструкция для сайта и приложения — отмена за 2 минуты."
    )
    canonical = f"{DOMAIN}/cancel/{s['slug']}.html"

    steps_ld = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": title,
        "description": description,
        "step": [
            {"@type": "HowToStep", "position": i + 1, "text": st}
            for i, st in enumerate(s["web_steps"])
        ],
        "totalTime": "PT2M",
    }
    import json

    steps_json = json.dumps(steps_ld, ensure_ascii=False, indent=2)

    web_lis = "\n".join(
        f'        <li><span class="num">{i + 1}</span><p>{esc(st)}</p></li>'
        for i, st in enumerate(s["web_steps"])
    )
    app_block = ""
    if s["app_steps"]:
        app_lis = "\n".join(
            f'        <li><span class="num">{i + 1}</span><p>{esc(st)}</p></li>'
            for i, st in enumerate(s["app_steps"])
        )
        app_block = f"""
      <h2>Как отменить в приложении</h2>
      <ol class="steps">
{app_lis}
      </ol>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
{METRIKA}
<meta property="og:type" content="article">
<meta property="og:site_name" content="SubPing">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<link rel="icon" type="image/png" href="../favicon.png">
<script type="application/ld+json">
{steps_json}
</script>
<style>
  :root{{ --bg:#0b0c10; --surface:#15161d; --surface-2:#1c1e29; --border:#272a38;
    --text:#f1f2f6; --text-2:#9497a8; --muted:#5c5f70; --accent:#818cf8; --warn:#eab308; }}
  *{{ box-sizing:border-box; }}
  body{{ margin:0; background:var(--bg); color:var(--text);
    font-family:-apple-system,'Segoe UI',Roboto,Inter,sans-serif; line-height:1.6; }}
  .wrap{{ max-width:640px; margin:0 auto; padding:24px 16px 48px; }}
  header{{ display:flex; align-items:center; gap:8px; margin-bottom:28px; }}
  .logo{{ width:32px; height:32px; border-radius:8px; background:#6366f1;
    display:flex; align-items:center; justify-content:center; color:#fff;
    font-weight:800; font-size:15px; text-decoration:none; }}
  header a.brand{{ color:var(--text); font-weight:700; text-decoration:none; }}
  h1{{ font-size:24px; line-height:1.25; margin:0 0 12px; }}
  h2{{ font-size:17px; margin:28px 0 12px; }}
  .lead{{ color:var(--text-2); font-size:15px; margin:0 0 16px; }}
  .price-tag{{ display:inline-block; background:var(--surface-2); border:1px solid var(--border);
    border-radius:999px; padding:4px 12px; font-size:13px; color:var(--accent); margin-bottom:20px; }}
  .quick{{ background:var(--surface); border:1px solid var(--border); border-radius:14px;
    padding:16px; margin:0 0 8px; font-size:14px; }}
  .quick b{{ color:var(--warn); }}
  ol.steps{{ list-style:none; margin:0; padding:0; }}
  ol.steps li{{ display:flex; gap:12px; background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:12px 14px; margin-bottom:10px; font-size:14px; }}
  ol.steps li p{{ margin:0; }}
  .num{{ flex-shrink:0; width:24px; height:24px; border-radius:50%; background:rgba(99,102,241,.15);
    color:var(--accent); font-weight:700; font-size:13px; display:flex; align-items:center; justify-content:center; margin-top:1px; }}
  .note{{ background:rgba(234,179,8,.08); border:1px solid rgba(234,179,8,.25); border-radius:12px;
    padding:14px; font-size:13.5px; margin:20px 0; }}
  .note b{{ color:var(--warn); }}
  .after{{ font-size:14px; color:var(--text-2); }}
  .cta{{ background:linear-gradient(135deg,#1c1e29,#15161d); border:1px solid rgba(99,102,241,.4);
    border-radius:16px; padding:22px; text-align:center; margin:32px 0 8px; }}
  .cta h2{{ margin:0 0 8px; font-size:17px; }}
  .cta p{{ font-size:13.5px; color:var(--text-2); margin:0 0 16px; }}
  .cta a.btn{{ display:inline-block; background:#6366f1; color:#fff; font-weight:600;
    text-decoration:none; padding:12px 24px; border-radius:10px; font-size:15px; }}
  .cta a.btn:hover{{ background:#4f46e5; }}
  .tips{{ font-size:13.5px; color:var(--text-2); border-left:3px solid var(--accent);
    padding-left:14px; margin-top:24px; }}
  footer{{ margin-top:40px; padding-top:16px; border-top:1px solid var(--border);
    font-size:12.5px; color:var(--muted); display:flex; flex-wrap:wrap; gap:14px; }}
  footer a{{ color:var(--text-2); text-decoration:none; }}
  footer a:hover{{ color:var(--accent); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="logo" href="../index.html">S</a>
    <a class="brand" href="../index.html">SubPing — трекер подписок</a>
  </header>

  <h1>Как отменить подписку {esc(s['name'])}</h1>
  <p class="lead">{esc(s['lead'])}</p>
  <span class="price-tag">{esc(s['price'])} · автопродление</span>

  <div class="quick">Коротко: зайдите в личный кабинет сервиса → раздел <b>«Подписка» / «Управление подпиской»</b> → <b>«Отключить автопродление»</b>. Доступ сохранится до конца оплаченного периода.</div>

  <h2>Пошагово на сайте</h2>
  <ol class="steps">
{web_lis}
  </ol>
{app_block}
  <div class="note"><b>Важно:</b> {esc(STORE_NOTE)}</div>

  <h2>Что будет после отмены</h2>
  <p class="after">{esc(s['after'])}</p>

  <div class="cta">
    <h2>Проверьте остальные подписки</h2>
    <p>Раз в месяц деньги уходят за сервисы, которыми вы не пользуетесь. SubPing собирает все подписки в одном месте и напоминает о списаниях заранее.</p>
    <a class="btn" href="../index.html">Попробовать бесплатно</a>
    <p style="margin-top:12px;font-size:12px;">Бесплатно до 3 подписок · без привязки карты</p>
  </div>

  <p class="tips">{esc(s['tips'])}</p>

  <footer>
    <a href="index.html">Все инструкции по отмене</a>
    <a href="../index.html">SubPing</a>
    <a href="../contacts.html">Контакты</a>
    <a href="../offer.html">Оферта</a>
    <a href="../privacy_policy.html">Конфиденциальность</a>
  </footer>
</div>
</body>
</html>
"""


def hub_html(services):
    items = "\n".join(
        f'    <li><a href="{s["slug"]}.html">Как отменить {esc(s["name"])}</a><span>{esc(s["price"])}</span></li>'
        for s in services
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Как отменить подписку: инструкции для популярных сервисов — SubPing</title>
<meta name="description" content="Пошаговые инструкции: как отменить подписку Яндекс Плюс, Кинопоиск, Telegram Premium, Spotify, Ozon Premium и других сервисов и отключить автопродление.">
<link rel="canonical" href="{DOMAIN}/cancel/">
{METRIKA}
<link rel="icon" type="image/png" href="../favicon.png">
<style>
  :root{{ --bg:#0b0c10; --surface:#15161d; --border:#272a38; --text:#f1f2f6;
    --text-2:#9497a8; --muted:#5c5f70; --accent:#818cf8; }}
  *{{ box-sizing:border-box; }}
  body{{ margin:0; background:var(--bg); color:var(--text);
    font-family:-apple-system,'Segoe UI',Roboto,Inter,sans-serif; line-height:1.6; }}
  .wrap{{ max-width:640px; margin:0 auto; padding:24px 16px 48px; }}
  header{{ display:flex; align-items:center; gap:8px; margin-bottom:28px; }}
  .logo{{ width:32px; height:32px; border-radius:8px; background:#6366f1;
    display:flex; align-items:center; justify-content:center; color:#fff;
    font-weight:800; font-size:15px; text-decoration:none; }}
  header a.brand{{ color:var(--text); font-weight:700; text-decoration:none; }}
  h1{{ font-size:24px; line-height:1.25; margin:0 0 12px; }}
  .lead{{ color:var(--text-2); font-size:15px; margin:0 0 24px; }}
  ul.list{{ list-style:none; margin:0; padding:0; }}
  ul.list li{{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
    padding:13px 16px; margin-bottom:10px; display:flex; justify-content:space-between;
    align-items:center; gap:12px; }}
  ul.list a{{ color:var(--text); text-decoration:none; font-size:14.5px; font-weight:600; }}
  ul.list a:hover{{ color:var(--accent); }}
  ul.list span{{ color:var(--muted); font-size:12.5px; white-space:nowrap; }}
  .cta{{ text-align:center; margin-top:32px; font-size:14px; color:var(--text-2); }}
  .cta a{{ color:var(--accent); }}
  footer{{ margin-top:40px; padding-top:16px; border-top:1px solid var(--border);
    font-size:12.5px; color:var(--muted); display:flex; flex-wrap:wrap; gap:14px; }}
  footer a{{ color:var(--text-2); text-decoration:none; }}
  footer a:hover{{ color:var(--accent); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="logo" href="../index.html">S</a>
    <a class="brand" href="../index.html">SubPing — трекер подписок</a>
  </header>
  <h1>Как отменить подписку: инструкции</h1>
  <p class="lead">Выберите сервис — внутри пошаговая инструкция, как отключить автопродление с сайта и из приложения.</p>
  <ul class="list">
{items}
  </ul>
  <div class="cta">Отменили одну? Проверьте остальные — <a href="../index.html">SubPing покажет все списания и напомнит о следующих</a>.</div>
  <footer>
    <a href="../index.html">SubPing</a>
    <a href="../contacts.html">Контакты</a>
    <a href="../offer.html">Оферта</a>
    <a href="../privacy_policy.html">Конфиденциальность</a>
  </footer>
</div>
</body>
</html>
"""


def sitemap_xml(services):
    today = datetime.date.today().isoformat()
    urls = [("https://subping.ru/", "daily", "1.0")]
    urls.append(("https://subping.ru/cancel/", "weekly", "0.8"))
    for s in services:
        urls.append((f"https://subping.ru/cancel/{s['slug']}.html", "monthly", "0.6"))
    body = "\n".join(
        f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{prio}</priority>
  </url>"""
        for loc, freq, prio in urls
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for s in SERVICES:
        path = os.path.join(OUT_DIR, f"{s['slug']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page_html(s))
        print("wrote", os.path.relpath(path, ROOT))
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(hub_html(SERVICES))
    print("wrote", os.path.relpath(os.path.join(OUT_DIR, "index.html"), ROOT))
    sitemap_path = os.path.join(ROOT, "frontend", "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap_xml(SERVICES))
    print("wrote", os.path.relpath(sitemap_path, ROOT))


if __name__ == "__main__":
    main()
