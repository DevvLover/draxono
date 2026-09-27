# HSL Captcha Solver API

A high-performance Python implementation for automated HSL proof-of-work computation, telemetry generation, and hCaptcha solving powered by NopeCHA recognition.

> [!NOTE]
> **Open Source Release**: This project was previously sold by [@draxonv1](https://github.com/draxonv1) for **$50 per person**. It is now completely free and open-source for everyone.
>
> For queries, feedback, or bug reports, please open an issue under the [GitHub Issues](https://github.com/DevvLover/draxono/issues) section.

---

## Features

- **PoW Computation**: Fast local HSL (SHA-1 proof-of-work) solver.
- **Dynamic Asset Tracking**: Automatically discovers and fetches the latest hCaptcha `checksiteconfig` hashes.
- **Telemetry Simulation**: Generates realistic browser telemetry and motion vector payloads.
- **Server API**: Built-in Flask HTTP server (`/solve`, `/health`) supporting key pooling and rotation via `keys/keys.txt`.
- **Colored Logging**: Standardized ANSI status logging (`[*] INFO`, `[+] SUCCESS`, `[-] ERROR`).

---

## Installation

```bash
git clone https://github.com/DevvLover/draxono.git
cd draxono
pip install -r requirements.txt
```

---

## Configuration

Add your NopeCHA API key to `keys/keys.txt` (one key per line):

```text
# keys/keys.txt
sub_1U3hsasawBt6pt892haudkT
```

---

## Usage

### 1. Start the API Server

```bash
python server.py --host 127.0.0.1 --port 8000
```

### 2. Client Test / Demo

Run the client demo to request a solve from the server:

```bash
python tests/solve_demo.py 
```

---

## Disclaimer

> **IMPORTANT DISCLAIMER**
> 
> This repository and its contents are provided strictly for **educational and research purposes**. 
> The author does not endorse, encourage, or support any unlawful activity, unauthorized automated access, or violation of any terms of service.
> Use this software at your own risk. The author assumes no responsibility or liability for any misuse, damages, account suspensions, or legal consequences arising from the use of this codebase.

---

## License

This project is licensed under the **MIT License**.

```text
MIT License

Copyright (c. 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
