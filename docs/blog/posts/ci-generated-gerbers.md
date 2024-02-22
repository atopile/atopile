---
date: 2024-02-02
authors: [matt]
description: >
  CI for electronics
categories:
  - Release
links:
---

# Trivial mistakes are expensive 🤑

Continuous integration / continuous deployment (CI/CD) is does things in software like running tests and deploying code automatically.

We've unfortunately been a little too responsible for some pretty expensive trivial mistakes in the past, so it's a key thing we wanted to focus on in `atopile`.

Instead of all shaking hands and totally agreeing that this local export named "pcb-final-final-final" is what we're going to spend serious money on - we can generate the manufacturing files on a trusted server

<picture>
    <source type="image/avif" srcset="/assets/images/ci-generated-gerbers.avif" />
    <img src="/assets/images/ci-generated-gerbers.gif" />
</picture>

... and stamp them with the precise version of the source-code used to create them!

![githash](/assets/images/ci-generated-gerbers-githash.png)

No more export mistakes 👌. Plus, it makes ordering boards super easy!

Matt
