---
date: 2024-02-09
authors: [matt]
description: >
  Why we created a language for hardware
categories:
  - About us
links:
---

# Why on earth did you create a new language? 🫣

It's a good question! Making people learn something new is a huge barrier to entry, ignores the wealth of community support from existing languages and can be a bit of a pain to maintain.

This iteration of the project actually came after first working with and then modifying an awesome project called SKiDL (https://github.com/devbisme/skidl). SKiDL takes the approach of using Python. Since it's procedural, turing complete and has a rich eco-system - people use to that and there aren't standard composable ways of designing things. Instead of describing your board, you (practically) write a script that generates your board. It entangles your targets with your source-code and can make it difficult to understand the ultimate outcome of what you've written.

We are trying to make it as readable and friendly as possible, our expectation is our users will likely have some experience with Python and perhaps a little C back in school, so making it clear and approachable is front of mind. Ideally some parts of code should "look" like the schematic, eg. `power.vcc ~> resistor ~> led ~> power.gnd`.

Units and tolerances are core to our language, the physical world is 'fuzzy' and having a good way to deal with those is pretty important. There's a few operators and first-class language features we wanted as well, (like units and tolerances eg. `3.3V +/- 100mV`) that just aren't the same when embedded in a string, or class init method.

Additionally, since it's a potentially very long program, it was hard to write good language support around (a language server for VSCode, a schematic visualiser etc...) that were snappy, responsive and lent to examining modules as well as the whole program.

Worth noting; we're probably going to try make our language more like Python, than less over the coming little while.

Happy coding! 🚀

-- Matt
