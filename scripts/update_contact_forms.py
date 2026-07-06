from pathlib import Path
import re

WORKER_URL = "https://refrdai-leads.bostonseoservice.workers.dev/"

SUBMIT_SCRIPT = r'''
<script id="lead-form-handler">
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("lead-form");
  if (!form) return;

  const pageUrlField = form.querySelector('[name="page_url"]');
  const cityField = form.querySelector('[name="city"]');
  const status = document.getElementById("form-status");
  const submitButton = form.querySelector('button[type="submit"]');

  if (pageUrlField) pageUrlField.value = window.location.href;

  if (cityField) {
    const geoPlace = document.querySelector('meta[name="geo.placename"]');
    cityField.value = geoPlace && geoPlace.content
      ? geoPlace.content.split(",")[0].trim()
      : "";
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (status) {
      status.style.display = "block";
      status.textContent = "Sending your request...";
    }

    if (submitButton) submitButton.disabled = true;

    try {
      if (pageUrlField) pageUrlField.value = window.location.href;

      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form)
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || "Form submission failed.");
      }

      if (status) {
        status.textContent = "Thank you. Your request has been sent.";
      }

      form.reset();
      if (pageUrlField) pageUrlField.value = window.location.href;
      if (cityField) {
        const geoPlace = document.querySelector('meta[name="geo.placename"]');
        cityField.value = geoPlace && geoPlace.content
          ? geoPlace.content.split(",")[0].trim()
          : "";
      }
    } catch (error) {
      console.error("Lead form error:", error);
      if (status) {
        status.textContent = "Something went wrong. Please call us directly at (321) 436-6595.";
      }
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
});
</script>
'''


def update_html(text: str) -> tuple[str, bool]:
    if 'onclick="submitForm()"' not in text:
        return text, False

    original = text

    text = text.replace(
        '<div class="appt-card-body">',
        f'<form class="appt-card-body" id="lead-form" action="{WORKER_URL}" method="POST">\n'
        ' <input type="hidden" name="city" value="">\n'
        ' <input type="hidden" name="page_url" value="">',
        1,
    )

    text = text.replace(
        '<input type="text" id="f-name" placeholder=',
        '<input type="text" id="f-name" name="name" autocomplete="name" required placeholder=',
        1,
    )
    text = text.replace(
        '<input type="tel" id="f-phone" placeholder=',
        '<input type="tel" id="f-phone" name="phone" autocomplete="tel" required placeholder=',
        1,
    )
    text = text.replace(
        '<input type="email" id="f-email" placeholder=',
        '<input type="email" id="f-email" name="email" autocomplete="email" placeholder=',
        1,
    )
    text = text.replace(
        '<select id="f-pet">',
        '<select id="f-pet" name="property_type">',
        1,
    )
    text = text.replace(
        '<select id="f-service">',
        '<select id="f-service" name="service">',
        1,
    )
    text = text.replace(
        '<textarea id="f-msg" placeholder=',
        '<textarea id="f-msg" name="message" placeholder=',
        1,
    )
    text = text.replace(
        '<button class="btn-submit" onclick="submitForm()">',
        '<button class="btn-submit" type="submit">',
        1,
    )

    close_pattern = re.compile(
        r'(\s*</button>)\s*</div>\s*</div>\s*\n\s*</div>\s*</section>',
        re.MULTILINE,
    )
    replacement = (
        r'\1\n <p id="form-status" role="status" aria-live="polite" '
        r'style="display:none;margin-top:12px;font-size:14px;font-weight:600;color:var(--heading);"></p>\n'
        r' </form>\n </div>\n\n </div>\n</section>'
    )
    text, count = close_pattern.subn(replacement, text, count=1)

    if count != 1:
        raise RuntimeError("Could not locate the appointment-card closing markup")

    if 'id="lead-form-handler"' not in text:
        text = text.replace('</body>', SUBMIT_SCRIPT + '\n</body>', 1)

    required_markers = [
        'id="lead-form"',
        'name="name"',
        'name="phone"',
        'name="email"',
        'name="property_type"',
        'name="service"',
        'name="message"',
        'name="page_url"',
        'type="submit"',
        'id="lead-form-handler"',
    ]

    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise RuntimeError(f"Updated form is missing markers: {missing}")

    return text, text != original


def main() -> None:
    updated = []
    skipped = []

    for path in sorted(Path('.').rglob('*.html')):
        text = path.read_text(encoding='utf-8')
        new_text, changed = update_html(text)

        if changed:
            path.write_text(new_text, encoding='utf-8', newline='')
            updated.append(str(path))
        else:
            skipped.append(str(path))

    remaining = []
    for path in sorted(Path('.').rglob('*.html')):
        if 'onclick="submitForm()"' in path.read_text(encoding='utf-8'):
            remaining.append(str(path))

    if remaining:
        raise RuntimeError(f"Old submitForm buttons remain in: {remaining}")

    print(f"Updated {len(updated)} HTML files.")
    print(f"Skipped {len(skipped)} HTML files without the old form.")


if __name__ == '__main__':
    main()
