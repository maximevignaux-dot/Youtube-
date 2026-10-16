// Tests des fonctions de paiement, avec Stripe et Printful simulés (aucun appel réel).
// Lancer : node tests/test_paiement.mjs
import { mkdtempSync, mkdirSync, copyFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHmac } from "node:crypto";
import assert from "node:assert/strict";

const ici = dirname(fileURLToPath(import.meta.url));
const tmp = mkdtempSync(join(tmpdir(), "boutique-"));
mkdirSync(join(tmp, "functions/api"), { recursive: true });
mkdirSync(join(tmp, "lib"));
for (const f of ["checkout.js", "stripe-webhook.js"]) copyFileSync(join(ici, "../functions/api", f), join(tmp, "functions/api", f));
writeFileSync(join(tmp, "lib/catalogue.js"), `
export const CATALOGUE = {"corse-klaxon": {"titre": "T-shirt Corse", "prix": 29.9, "visible": true, "photo": "/img/corse-klaxon/partage.jpg", "tailles": {"M": 111, "L": 112}},
 "brouillon": {"titre": "Pas en vente", "prix": 29.9, "visible": false, "photo": "/x.jpg", "tailles": {"M": 9}}};
export const LIVRAISON = {"mode": "forfait", "forfait": 4.9};
export const PAYS = ["FR", "BE"];`);
const { onRequestPost: checkout } = await import(join(tmp, "functions/api/checkout.js"));
const wh = await import(join(tmp, "functions/api/stripe-webhook.js"));

let appels = [];
globalThis.fetch = async (url, opt) => { appels.push({ url, opt }); return globalThis.reponse(url, opt); };
const req = (body, headers = {}) => new Request("https://boutique.test/api/x", { method: "POST", body, headers });
const env = { STRIPE_SECRET_KEY: "sk_test_x", STRIPE_WEBHOOK_SECRET: "whsec_test", PRINTFUL_TOKEN: "pf", SITE_URL: "https://boutique.test" };

// 1. Le prix vient du serveur, pas du navigateur
globalThis.reponse = () => new Response(JSON.stringify({ url: "https://checkout.stripe.com/c/pay/x" }), { status: 200 });
let r = await checkout({ request: req(JSON.stringify({ items: [{ id: "corse-klaxon", taille: "L", qte: 2, prix: 0.01 }] })), env });
assert.equal(r.status, 200);
assert.equal((await r.json()).url, "https://checkout.stripe.com/c/pay/x");
const p = new URLSearchParams(appels[0].opt.body.toString());
assert.equal(p.get("line_items[0][price_data][unit_amount]"), "2990");
assert.equal(p.get("line_items[0][quantity]"), "2");
assert.equal(p.get("metadata[articles]"), "112x2");
assert.equal(p.get("shipping_options[0][shipping_rate_data][fixed_amount][amount]"), "490");
assert.equal(p.get("success_url"), "https://boutique.test/merci/?commande={CHECKOUT_SESSION_ID}");
console.log("✔ prix recalculé côté serveur (29,90 € malgré 0,01 € envoyé), quantité, livraison, articles Printful");

// 2. Refus : t-shirt en brouillon, taille inconnue, quantité folle bornée
appels = [];
r = await checkout({ request: req(JSON.stringify({ items: [{ id: "brouillon", taille: "M", qte: 1 }] })), env });
assert.equal(r.status, 400);
r = await checkout({ request: req(JSON.stringify({ items: [{ id: "corse-klaxon", taille: "XXXXL", qte: 1 }] })), env });
assert.equal(r.status, 400);
r = await checkout({ request: req("pas du json"), env });
assert.equal(r.status, 400);
assert.equal(appels.length, 0);
r = await checkout({ request: req(JSON.stringify({ items: [{ id: "corse-klaxon", taille: "M", qte: 999 }] })), env });
assert.equal(new URLSearchParams(appels[0].opt.body.toString()).get("line_items[0][quantity]"), "10");
console.log("✔ refuse brouillon / taille inconnue / panier illisible, quantité bornée à 10");

// 3. Webhook : signature
const session = { id: "cs_test_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9", payment_status: "paid", amount_total: 6470,
  metadata: { articles: "112x2" }, customer_details: { email: "client@exemple.fr", phone: "+33600000000", name: "Jean Test" },
  collected_information: { shipping_details: { name: "Jean Test", address: { line1: "1 rue du Port", line2: null, city: "Ajaccio", postal_code: "20000", country: "FR", state: null } } } };
const corps = JSON.stringify({ type: "checkout.session.completed", data: { object: session } });
const t = Math.floor(Date.now() / 1000);
const sig = createHmac("sha256", "whsec_test").update(`${t}.${corps}`).digest("hex");
appels = [];
r = await wh.onRequestPost({ request: req(corps, { "stripe-signature": `t=${t},v1=deadbeef` }), env });
assert.equal(r.status, 400);
r = await wh.onRequestPost({ request: req(corps, { "stripe-signature": `t=${t - 1000},v1=${sig}` }), env });
assert.equal(r.status, 400);
assert.equal(appels.length, 0);
console.log("✔ webhook : refuse une fausse signature et une signature trop vieille");

// 4. Webhook valide → commande Printful en brouillon
globalThis.reponse = () => new Response(JSON.stringify({ code: 200, result: { id: 1 } }), { status: 200 });
r = await wh.onRequestPost({ request: req(corps, { "stripe-signature": `t=${t},v1=${sig}` }), env });
assert.equal(r.status, 200);
assert.equal(appels[0].url, "https://api.printful.com/orders");
const cmd = JSON.parse(appels[0].opt.body);
assert.deepEqual(cmd.items, [{ sync_variant_id: 112, quantity: 2 }]);
assert.equal(cmd.recipient.city, "Ajaccio");
assert.equal(cmd.recipient.country_code, "FR");
assert.equal(cmd.external_id.length, 32);
console.log("✔ webhook valide → commande Printful en brouillon, bonne adresse et bons articles");

// 5. Phase 2 : confirmation automatique ; doublon ignoré ; erreur → Stripe réessaiera
appels = [];
r = await wh.onRequestPost({ request: req(corps, { "stripe-signature": `t=${t},v1=${sig}` }), env: { ...env, PRINTFUL_AUTO_CONFIRM: "1" } });
assert.equal(appels[0].url, "https://api.printful.com/orders?confirm=true");
globalThis.reponse = () => new Response(JSON.stringify({ code: 400, error: { message: "Order with this External ID already exists" } }), { status: 400 });
r = await wh.onRequestPost({ request: req(corps, { "stripe-signature": `t=${t},v1=${sig}` }), env });
assert.equal(r.status, 200);
globalThis.reponse = () => new Response(JSON.stringify({ code: 500, error: { message: "boom" } }), { status: 500 });
r = await wh.onRequestPost({ request: req(corps, { "stripe-signature": `t=${t},v1=${sig}` }), env });
assert.equal(r.status, 500);
console.log("✔ phase 2 confirme seule ; doublon ignoré ; erreur Printful → Stripe réessaie");
console.log("\nTous les tests passent.");
