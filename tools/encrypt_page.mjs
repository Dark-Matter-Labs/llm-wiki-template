#!/usr/bin/env node
// encrypt_page.mjs — lock a page behind a password before it goes on a wiki's public site.
//
// Adapted on 12 October 2026 from prateek-llm-wiki's encrypt_lens.mjs, for the "Needs you" page,
// which carries a wiki's private items. The published file holds only ciphertext: AES-256-GCM, the
// key derived from the password by PBKDF2-SHA-256 (600,000 rounds), with a fresh random salt and IV
// on every build. The browser decrypts it after the password is typed; nothing is sent anywhere.
//
// Two choices differ from the lens, both from a review of the lens the same day:
//   - No "remember on this device". Every Dark Matter Labs site shares one web address, so a key
//     saved in the browser could be read by a script on any of them. The password is asked each time.
//   - A fresh salt per build, since there is no remembered key to keep working across builds.
//
// It is only as strong as the password: anyone can download the file and guess offline. The
// password must be 12 characters or more; four or more random words is the advice.
//
// The password comes from the NEEDS_YOU_PASSWORD environment variable, set as a hidden setting
// (a secret) in the wiki. It is never written to the repository or printed.
//
// Usage: NEEDS_YOU_PASSWORD=… node tools/encrypt_page.mjs <in.html> <out.html> <heading, e.g. "Leon’s wiki">

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { webcrypto as crypto } from "node:crypto";

const [src, out, name] = process.argv.slice(2);
const password = process.env.NEEDS_YOU_PASSWORD;
if (!src || !out || !name) {
  console.error("usage: node tools/encrypt_page.mjs <in.html> <out.html> <heading>");
  process.exit(2);
}
if (!password || password.length < 12) {
  console.error("Set NEEDS_YOU_PASSWORD (12 characters or more). Nothing was written.");
  process.exit(2);
}

const ROUNDS = 600000;
const html = readFileSync(src, "utf8");
const salt = crypto.getRandomValues(new Uint8Array(16));
const iv = crypto.getRandomValues(new Uint8Array(12));
const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
const key = await crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt, iterations: ROUNDS }, base,
                                          { name: "AES-GCM", length: 256 }, false, ["encrypt"]);
const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(html)));
const b64 = (u) => Buffer.from(u).toString("base64");
const esc = (t) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const who = esc(name);

const page = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>Needs you · ${who}</title>
<meta name="description" content="A private view of what needs attention in ${who}. Password required.">
<meta property="og:title" content="Needs you · ${who}">
<meta property="og:description" content="A private view. Password required.">
<meta property="og:image" content="../assets/social-card.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400&family=Inter:wght@400;500&family=DM+Mono:wght@500&display=swap">
<style>
:root{--paper:#F6F1E5;--raised:#FCFAF5;--rule:rgba(16,31,36,.16);--ink:#101F24;--muted:#374E4A;--weak:#516962;--warn:#A13E25;
  --serif:"Crimson Pro",Georgia,serif;--sans:Inter,system-ui,sans-serif;--mono:"DM Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root{--paper:#101F2D;--raised:#152939;--rule:rgba(246,241,229,.18);--ink:#F6F1E5;--muted:#B4C0B9;--weak:#93A39D;--warn:#F58A57}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 var(--sans)}
a.skip{position:absolute;left:-999px}a.skip:focus{left:16px;top:16px}
main{min-height:100vh;display:grid;place-items:center;padding:24px 16px}
.box{width:min(400px,100%)}
.kind{font:500 12px/1 var(--mono);letter-spacing:.06em;color:var(--weak)}
h1{font:400 44px/1.05 var(--serif);margin:10px 0 8px;letter-spacing:-.02em}
p{margin:0 0 18px;color:var(--muted)}
label{display:block;font:500 11.5px/1.3 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--weak);margin-bottom:6px}
input[type=password]{width:100%;font:16px/1.3 var(--sans);padding:12px 14px;border:1px solid var(--rule);border-radius:10px;background:var(--raised);color:var(--ink)}
button{margin-top:14px;font:500 15px/1 var(--sans);background:var(--ink);color:var(--paper);border:0;border-radius:10px;padding:13px 22px;min-height:44px;cursor:pointer}
button[disabled]{opacity:.6;cursor:progress}
input:focus-visible,button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.msg{min-height:1.6em;margin-top:12px;font-size:14px;color:var(--warn)}
.foot{margin-top:28px;font:400 12px/1.5 var(--mono);color:var(--weak)}
</style>
</head>
<body>
<a class="skip" href="#pw">Skip to password</a>
<main id="main">
  <form class="box" id="f" autocomplete="on">
    <span class="kind">Private</span>
    <h1>Needs you</h1>
    <p>What needs attention in ${who}. Enter the password to open it.</p>
    <input type="text" name="username" value="needs-you" autocomplete="username" hidden>
    <label for="pw">Password</label>
    <input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
    <button id="go" type="submit">Open</button>
    <div class="msg" id="msg" role="alert" aria-live="assertive"></div>
    <div class="foot">Nothing here is readable without the password, and nothing is sent anywhere.</div>
  </form>
</main>
<script>
(function(){
  var SALT = "${b64(salt)}"; var IV = "${b64(iv)}"; var CT = "${b64(ct)}"; var ROUNDS = ${ROUNDS};
  var msg = document.getElementById("msg"), go = document.getElementById("go");
  function say(t){ msg.textContent = t; }
  function bytes(b){ var s = atob(b), u = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u; }
  function show(html){
    try { document.open(); document.write(html); document.close(); return; } catch(e){}
    var f = document.createElement("iframe");
    f.setAttribute("title", "Needs you");
    f.style.cssText = "position:fixed;inset:0;width:100%;height:100%;border:0";
    document.body.innerHTML = ""; document.body.style.margin = "0"; f.srcdoc = html; document.body.appendChild(f);
  }
  if (!(window.crypto && crypto.subtle && window.TextDecoder)) {
    say("This browser can't unlock the page. Open the link in Safari, Chrome, Firefox or Edge, not inside another app.");
    go.disabled = true; return;
  }
  document.getElementById("f").addEventListener("submit", async function(e){
    e.preventDefault(); go.disabled = true; go.textContent = "Opening…"; say("");
    try {
      var base = await crypto.subtle.importKey("raw", new TextEncoder().encode(document.getElementById("pw").value.trim()), "PBKDF2", false, ["deriveKey"]);
      var key = await crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: bytes(SALT), iterations: ROUNDS }, base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
      var html = new TextDecoder().decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv: bytes(IV) }, key, bytes(CT)));
      show(html);
    } catch(err) {
      go.disabled = false; go.textContent = "Open";
      say(err && err.name === "OperationError" ? "That password did not open it. Check it and try again." : "The page could not be unlocked in this browser. Try Safari, Chrome, Firefox or Edge.");
      document.getElementById("pw").select();
    }
  });
})();
</script>
</body>
</html>
`;

mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, page);
console.log(`locked ${src} -> ${out} (${Math.round(page.length / 1024)} KB)`);
