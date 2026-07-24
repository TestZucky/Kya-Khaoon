# Privacy and data handling

Kya Khaoon decides what you should eat. To do that it needs to know what you
can't eat, what you like, and what you've had lately — and nothing else. This
page says exactly what's held, where it goes, and how to get rid of it.

## What we collect

| What | Why | Kept |
|---|---|---|
| Phone number, **or** a Google account (name, email), **or** a browser-generated device id | To know it's the same person across visits. Any one of them is enough — you're never asked for all three | Until you ask us to delete it |
| Diet, allergies, avoided ingredients | The only answers where being wrong means suggesting food you can't eat | Until you change it |
| Budget, cuisines, spice tolerance, goal | To rank dishes; they never rule one out | Until you change it |
| Height, weight, home state — all optional | To tilt picks gently. Skipping them never blocks anything | Until you change it |
| Mood, party size, meal period | These change meal to meal, so they're tied to one deck and never treated as truth about you | One deck |
| Your swipes, and the reason you gave for a left | The only thing that learns from you | History |
| Your Swiggy address id, and your Swiggy OAuth tokens | Every menu and restaurant lookup is scoped to a delivery address | Until you disconnect |

**We never ask for and never store** a payment card, a Swiggy password, or your
precise location. We don't use tracking cookies or advertising SDKs, and we don't
sell or share data for advertising.

## Where it goes

Your data reaches four outside parties, each for one job.

**Swiggy** — over their MCP server, using *your* OAuth token, forwarded per
request. We read your addresses, your past orders, live menus and restaurants,
and we build a cart. **We never place an order and never touch payment** —
there's no order-placement endpoint in the codebase, and a test fails if one is
ever called. Checkout happens in Swiggy, as it always did.

**OpenAI** — to pick the dish ideas. It receives a short taste brief and nothing
that identifies you: diet, allergies, cuisines, goal, spice tolerance, budget
ceiling, current meal period, mood, hunger, who you're eating with, home region,
a BMI *band* if you gave height and weight, and a one-line summary of the dishes
and cuisines you order often with your typical spend. **No name, phone, email,
address, user id or Swiggy token is ever sent to the model.** OpenAI states that
content submitted through their API is not used to train their models.

**Google** — only if you choose Google Sign-In. We verify the ID token and keep
the account id, email and name.

**Twilio** — only your phone number, only to deliver a login code. In
development, codes are printed to the log instead and no SMS is sent.

## Where it lives

One PostgreSQL database, in the region named in our Swiggy Builders application.

Your **Swiggy tokens are encrypted at rest** with a key held outside the
database, so a leaked backup or disk snapshot can't be used to act as you. Login
codes are stored only as a hash — never the code itself. OAuth codes and states
are stripped out of logs before they're written, and email addresses are masked.

## Getting your data out, or deleted

Email **rajawapp@gmail.com** and we'll export or delete everything tied to your
account within **30 days**. Deleting removes your profile, swipes, sessions and
stored Swiggy tokens.

There's no self-serve delete button yet, and no in-app "disconnect Swiggy"
either — being straight about that rather than implying they exist. Both are the
next things on this list. Until then, email us and we'll clear your stored Swiggy
tokens within 30 days; you can also revoke this app's access from Swiggy's own
account settings at any time, which stops it immediately and needs nothing from
us.

## Children

Not intended for anyone under 13, and we don't knowingly keep data from them.

## Changes

Material changes will be noted in this file's git history, which is public.
