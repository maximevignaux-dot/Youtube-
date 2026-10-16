// POST /api/stripe-webhook : Stripe prévient qu'un paiement est réussi → on crée la commande chez Printful.
// Phase 1 (PRINTFUL_AUTO_CONFIRM=0) : commande en BROUILLON, Maxime confirme dans Printful.
// Phase 2 (PRINTFUL_AUTO_CONFIRM=1) : commande confirmée automatiquement, Printful imprime et expédie.

const ok = (txt = "ok", status = 200) => new Response(txt, { status });

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function egal(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

// Vérifie la signature Stripe (en-tête Stripe-Signature : t=...,v1=...) sur le corps brut.
export async function signatureValide(brut, entete, secret, maintenant = Date.now() / 1000) {
  if (!entete || !secret) return false;
  const parts = {};
  const v1 = [];
  for (const morceau of entete.split(",")) {
    const [k, v] = morceau.split("=");
    if (k === "t") parts.t = v;
    if (k === "v1") v1.push(v);
  }
  if (!parts.t || !v1.length || Math.abs(maintenant - Number(parts.t)) > 300) return false;
  const attendu = await hmacHex(secret, `${parts.t}.${brut}`);
  return v1.some((s) => egal(s, attendu));
}

export function commandePrintful(session) {
  const liv = session.collected_information?.shipping_details || session.shipping_details || {};
  const a = liv.address || {};
  const client = session.customer_details || {};
  const items = (session.metadata?.articles || "")
    .split(",")
    .filter(Boolean)
    .map((x) => {
      const [v, q] = x.split("x");
      return { sync_variant_id: Number(v), quantity: Number(q) };
    });
  return {
    external_id: session.id.slice(-32), // Printful refuse deux commandes avec le même identifiant : pas de doublon si Stripe renvoie l'événement
    shipping: "STANDARD",
    recipient: {
      name: liv.name || client.name || "",
      address1: a.line1 || "",
      address2: a.line2 || "",
      city: a.city || "",
      zip: a.postal_code || "",
      country_code: a.country || "",
      state_code: a.state || "",
      email: client.email || "",
      phone: client.phone || "",
    },
    items,
  };
}

async function prevenirMaxime(env, sujet, texte) {
  if (!env.RESEND_API_KEY || !env.EMAIL_MAXIME) return;
  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: "Boutique <onboarding@resend.dev>", to: [env.EMAIL_MAXIME], subject: sujet, text: texte }),
  }).catch(() => {});
}

export async function onRequestPost({ request, env }) {
  const brut = await request.text();
  if (!(await signatureValide(brut, request.headers.get("stripe-signature"), env.STRIPE_WEBHOOK_SECRET)))
    return ok("signature invalide", 400);

  const ev = JSON.parse(brut);
  if (ev.type !== "checkout.session.completed") return ok("ignoré");
  const session = ev.data.object;
  if (session.payment_status !== "paid") return ok("pas encore payé");

  const commande = commandePrintful(session);
  const auto = env.PRINTFUL_AUTO_CONFIRM === "1";
  const headers = { Authorization: `Bearer ${env.PRINTFUL_TOKEN}`, "Content-Type": "application/json" };
  if (env.PRINTFUL_STORE_ID) headers["X-PF-Store-Id"] = env.PRINTFUL_STORE_ID;

  const r = await fetch(`https://api.printful.com/orders${auto ? "?confirm=true" : ""}`, {
    method: "POST",
    headers,
    body: JSON.stringify(commande),
  });
  const rep = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = JSON.stringify(rep?.error || rep).toLowerCase();
    if (msg.includes("external") && msg.includes("exist")) return ok("déjà créée"); // Stripe a renvoyé l'événement
    console.log("Printful a refusé la commande :", msg);
    await prevenirMaxime(env, "⚠️ Commande payée mais PAS créée chez Printful",
      `Paiement Stripe ${session.id} reçu, mais Printful a répondu : ${msg}\nCrée la commande à la main dans Printful.`);
    return ok("erreur Printful", 500); // Stripe réessaiera plus tard
  }
  const total = ((session.amount_total || 0) / 100).toFixed(2).replace(".", ",");
  await prevenirMaxime(env, `🎉 Nouvelle commande : ${total} €`,
    `${commande.recipient.name} (${commande.recipient.city}) — ${commande.items.length} article(s).\n` +
    (auto ? "Commande confirmée automatiquement chez Printful." : "Commande en BROUILLON chez Printful : va la vérifier et la confirmer."));
  return ok("commande créée");
}
