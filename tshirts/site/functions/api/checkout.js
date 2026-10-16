// POST /api/checkout : reçoit le panier, recalcule les prix CÔTÉ SERVEUR, crée la session Stripe Checkout.
import { CATALOGUE, LIVRAISON, PAYS } from "../../lib/catalogue.js";

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

export async function onRequestPost({ request, env }) {
  let corps;
  try {
    corps = await request.json();
  } catch {
    return json({ erreur: "Panier illisible." }, 400);
  }
  const items = Array.isArray(corps?.items) ? corps.items : [];
  if (!items.length || items.length > 20) return json({ erreur: "Panier vide ou trop grand." }, 400);

  const site = (env.SITE_URL || new URL(request.url).origin).replace(/\/$/, "");
  const p = new URLSearchParams();
  p.append("mode", "payment");
  p.append("locale", "fr");
  p.append("success_url", `${site}/merci/?commande={CHECKOUT_SESSION_ID}`);
  p.append("cancel_url", `${site}/annule/`);
  p.append("phone_number_collection[enabled]", "true");
  PAYS.forEach((c, i) => p.append(`shipping_address_collection[allowed_countries][${i}]`, c));

  const articles = [];
  let n = 0;
  for (const it of items) {
    const prod = CATALOGUE[it?.id];
    if (!prod || !prod.visible) return json({ erreur: "Un t-shirt de ton panier n'est plus disponible." }, 400);
    const variante = prod.tailles[it.taille];
    if (!variante) return json({ erreur: "Taille indisponible." }, 400);
    const qte = Math.min(10, Math.max(1, parseInt(it.qte, 10) || 1));
    p.append(`line_items[${n}][quantity]`, String(qte));
    p.append(`line_items[${n}][price_data][currency]`, "eur");
    p.append(`line_items[${n}][price_data][unit_amount]`, String(Math.round(prod.prix * 100)));
    p.append(`line_items[${n}][price_data][product_data][name]`, `${prod.titre} – taille ${it.taille}`);
    p.append(`line_items[${n}][price_data][product_data][images][0]`, site + prod.photo);
    articles.push(`${variante}x${qte}`);
    n++;
  }
  // Ce qui part chez Printful après paiement (lu par le webhook, jamais par le navigateur).
  p.append("metadata[articles]", articles.join(","));
  p.append("payment_intent_data[metadata][articles]", articles.join(","));

  const port = LIVRAISON.mode === "offerte" ? 0 : Math.round(LIVRAISON.forfait * 100);
  p.append("shipping_options[0][shipping_rate_data][type]", "fixed_amount");
  p.append("shipping_options[0][shipping_rate_data][fixed_amount][amount]", String(port));
  p.append("shipping_options[0][shipping_rate_data][fixed_amount][currency]", "eur");
  p.append("shipping_options[0][shipping_rate_data][display_name]", port ? "Livraison suivie" : "Livraison offerte");

  const r = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: p,
  });
  const s = await r.json();
  if (!r.ok) {
    console.log("Stripe a refusé la session :", s?.error?.message);
    return json({ erreur: "Le paiement est indisponible pour le moment, réessaie dans un instant." }, 502);
  }
  return json({ url: s.url });
}
