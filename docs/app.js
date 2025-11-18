// ===== Kategória meghatározás egy termékre =====
function getCategoriesForItem(pid, it) {
  const cfg = PARTNERS.get(pid) || {};
  let cat = baseCategoryForPartner(pid, cfg);

  const text = (
    (it && it.title ? it.title : "") +
    " " +
    (it && it.desc ? it.desc : "")
  ).toLowerCase();

  const hasAny = (words) => words.some((w) => text.includes(w));

  // Ruházat / divat kulcsszavak (Tchibo miatt túltolva)
  const CLOTHES_WORDS = [
    "póló", "polo", "t-shirt", "t shirt",
    "pulóver", "pulover", "pulcsi",
    "ruha", "szoknya", "blúz", "bluz",
    "nadrág", "nadrag", "farmer",
    "ing", "felső", "felso", "overall",
    "leggings", "harisnya", "zokni",
    "pizsama", "hálóing", "haloing", "köntös", "kontos",
    "kabát", "kabat", "dzseki", "dzsekit",
    "melltartó", "melltarto", "fehérnemű", "fehernemu",
  ];

  const SHOES_WORDS = [
    "cipő", "cipo",
    "csizma", "bakancs",
    "szandál", "szandal",
    "papucs", "mokaszin", "loafer",
  ];

  const APPLIANCE_WORDS = [
    "mosógép", "mosogep",
    "mosogatógép", "mosogatogep",
    "mosó-szárító", "moso-szarito",
    "szárítógép", "szaritogep",
    "hűtőszekrény", "hutoszekreny",
    "fagyasztó", "fagyaszto",
    "sütő", "suto",
    "tűzhely", "tuzhely",
    "mikrohullámú", "mikrohullamu", "mikro",
    "porszívó", "porszivo", "robotporszívó", "robotporszivo",
    "gőztisztító", "goztisztito",
    "kávéfőző", "kavefozo",
    "turmix", "botmixer",
    "konyhagép", "konyhagep",
  ];

  const GARDEN_WORDS = [
    "kert", "kerti",
    "locsoló", "locsolo", "slag",
    "fűnyíró", "funyiro",
    "fűkasza", "fukasza",
    "láncfűrész", "lancfuresz",
    "metszőolló", "metszoollo",
    "gereblye",
    "ásó", "aso",
    "lapát", "lapat",
    "kerti szerszám",
    "magasnyomású mosó", "magasnyomasu moso",
  ];

  // Alap: partnerhez rendelt kategoriacímke
  if (cat === "kat-otthon") {
    // 1) Ruházat → Divat
    if (hasAny(CLOTHES_WORDS) || hasAny(SHOES_WORDS)) {
      cat = "kat-divat";

    // 2) Háztartási gép → Gépek
    } else if (hasAny(APPLIANCE_WORDS)) {
      cat = "kat-gepek";

    // 3) Kerti cucc → Kert
    } else if (hasAny(GARDEN_WORDS)) {
      cat = "kat-kert";
    }
  }

  if (cat === "kat-elektronika") {
    // Nagygépek elektronika helyett → Gépek
    if (hasAny(APPLIANCE_WORDS)) {
      cat = "kat-gepek";
    }
  }

  // Biztos fallback
  if (!cat) cat = "kat-multi";
  return [cat];
}
