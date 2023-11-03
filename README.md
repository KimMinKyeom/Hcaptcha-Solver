# Hcaptcha Solver

> **⚠️ Caution:** It's currently blocked by a security update (they've added a different, more varied Turing test than before).

Use AI to tackle and solve hcaptcha challenges seamlessly.



# Key Features
- Robust AI Capability: Trained on a dataset of over 30,000 images ensuring speed and precision.
- Proxy Support: Facilitates the use of HTTP proxies.


# Quick Example
```py
import hsolver, requests

session = requests.session()
# Optional: Update with proxy details if needed
# session.proxies.update({"http": "proxy_address", 'https': "proxy_address"})

print(hsolver.HcaptchaSolver(session).solve('site_key', 'host'))  # Ex.'4c672d35-0701-42b2-88c3-78380b0db560', 'discord.com'
```
