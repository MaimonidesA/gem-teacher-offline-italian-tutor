"""Small, explicit lesson plans and bounded evidence; no extra model calls."""
import copy
import json
import re
from .curriculum import BY_ID

# Each item is a learner action, not a number of messages or a teacher action.
OBJECTIVES = {
    "hello": [("Saluer et dire votre nom", "Greet someone and say your name"),
              ("Dire d’où vous venez", "Say where you are from"),
              ("Demander à l’autre comment il va", "Ask the other person how they are")],
    "cafe": [("Commander une boisson poliment", "Politely order a drink"),
             ("Demander le prix", "Ask the price"),
             ("Choisir comment payer et remercier", "Choose how to pay and say thank you")],
    "city": [("Demander où se trouve un lieu", "Ask where a place is"),
             ("Reformuler une direction reçue", "Restate a direction you were given"),
             ("Donner un itinéraire avec deux indications", "Give directions with two steps")],
    "food": [("Commander un plat", "Order a dish"),
             ("Exprimer un goût ou une restriction alimentaire", "Express a preference or dietary restriction"),
             ("Demander une recommandation ou l’addition", "Ask for a recommendation or the bill")],
    "daily": [("Décrire une activité du matin avec une heure", "Describe a morning activity with a time"),
              ("Décrire une autre habitude au présent", "Describe another habit in the present tense"),
              ("Comparer votre semaine et votre week-end", "Compare your weekday and weekend routines")],
    "travel": [("Demander un billet avec une destination", "Ask for a ticket to a destination"),
               ("Demander l’heure de départ", "Ask the departure time"),
               ("Réserver une chambre en précisant la durée", "Book a room and specify the length of the stay")],
    "stories": [("Raconter une action passée", "Describe a past action"),
                ("Ajouter qui était là ou ce qui s’est passé ensuite", "Add who was there or what happened next"),
                ("Dire comment vous vous êtes senti", "Say how you felt")],
    "free": [("Présenter un sujet qui vous intéresse", "Introduce a subject that interests you"),
             ("Donner un avis avec une raison", "Give an opinion and a reason"),
             ("Poser une question liée au sujet", "Ask a question related to the subject")],
}

# One short Italian grammar aside per lesson. Examples stay visible in recaps.
# Beginner and more advanced variants follow the session's chosen working level.
TIPS = {
    "hello": [
        ("Le verbe indique souvent la personne : on peut dire « sono » sans « io ».", "The verb often identifies the person: you can say ‘sono’ without ‘io’.", "Sono francese. / Io sono francese."),
        ("« Tu » est familier ; « Lei » est poli et prend la troisième personne du singulier.", "‘Tu’ is informal; polite ‘Lei’ takes the third-person singular verb.", "Come ti chiami? / Come si chiama?")],
    "cafe": [
        ("Les noms en -è accentué ne changent pas au pluriel. C’est l’article ou le nombre qui change.", "Nouns ending in stressed -è stay the same in the plural. The article or number changes.", "Un caffè, due caffè. / Il caffè, i caffè."),
        ("« Vorrei » est le conditionnel de volere : pratique pour demander poliment.", "‘Vorrei’ is the conditional of volere: useful for polite requests.", "Vorrei un tè. / Vorremmo due caffè.")],
    "city": [
        ("Beaucoup de noms en -e prennent -i au pluriel, même au féminin.", "Many nouns ending in -e take -i in the plural, including feminine nouns.", "La stazione → le stazioni."),
        ("Une préposition peut se combiner avec l’article : a + la devient alla, a + il devient al.", "A preposition can combine with an article: a + la becomes alla, a + il becomes al.", "Vado alla stazione e poi al mercato.")],
    "food": [
        ("Avec piacere, on dit « mi piace » pour une chose au singulier, « mi piacciono » au pluriel.", "With piacere, use ‘mi piace’ for a singular thing and ‘mi piacciono’ for plural things.", "Mi piace la pizza. / Mi piacciono gli gnocchi."),
        ("L’adjectif s’accorde avec le nom en genre et en nombre.", "An adjective agrees with its noun in gender and number.", "Un piatto caldo, due piatti caldi. / Una zuppa calda.")],
    "daily": [
        ("Pour l’heure, on dit « all’una », mais « alle » devant les autres heures.", "For clock times, use ‘all’una’ but ‘alle’ with the other hours.", "Pranzo all’una. / Mi alzo alle sette."),
        ("Les verbes réfléchis changent aussi de petit pronom selon la personne.", "Reflexive verbs change their small pronoun to match the person too.", "Mi alzo presto. / Ti alzi presto? / Ci alziamo presto.")],
    "travel": [
        ("Souvent, le pluriel masculin passe de -o à -i, et le féminin de -a à -e.", "Often, masculine plurals change -o to -i and feminine plurals change -a to -e.", "Un biglietto → due biglietti. / Una camera → due camere."),
        ("Le présent peut décrire un voyage futur si une date ou un mot comme domani précise le moment.", "The present tense can describe future travel when a date or a word such as domani makes the timing clear.", "Domani parto per Roma. / Partirò domani.")],
    "stories": [
        ("Le passato prossimo utilise avere ou essere et un participe passé.", "The passato prossimo uses avere or essere plus a past participle.", "Ho mangiato. / Sono arrivato. / Sono arrivata."),
        ("L’imperfetto décrit souvent le décor ou une habitude ; le passato prossimo raconte un événement terminé.", "The imperfetto often describes background or a habit; the passato prossimo tells a completed event.", "Pioveva quando sono arrivato.")],
    "free": [
        ("« Perché » sert à demander pourquoi, mais aussi à donner une raison.", "‘Perché’ can ask why, and it can also introduce a reason.", "Perché leggi? / Leggo perché mi piace."),
        ("Le conditionnel peut exprimer une envie ou une possibilité, pas seulement une demande polie.", "The conditional can express a wish or possibility, as well as a polite request.", "Mi piacerebbe leggere quel libro. / Potremmo parlarne.")],
}


def new_plan(topic, level, target):
    objectives = [{"id": f"step{i + 1}", "fr": fr, "en": en, "evidence": "", "turn": None}
                  for i, (fr, en) in enumerate(OBJECTIVES[topic])]
    grammar = None
    if target == "it":
        fr, en, example = TIPS[topic][int(level not in ("A0", "A1"))]
        grammar = {"fr": fr, "en": en, "example": example}
    vocabulary = [{"text": text, "translation": fr, "english": en, "base": "fr"}
                  for text, fr, en in BY_ID[topic]["phrases"]] if target == "it" else []
    return {"version": 1, "status": "active", "objectives": objectives, "grammar": grammar,
            "vocabulary": vocabulary, "recap": {}}


def read_plan(session):
    if session["mode"] == "coffee":
        return None
    value = session["lesson"]
    value = json.loads(value) if isinstance(value, str) else value
    return copy.deepcopy(value)


def pending_objective(plan):
    return next((o for o in (plan or {}).get("objectives", []) if not o["evidence"]), None)


def normalized(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def update_plan(plan, result, user_text, action, turn, base):
    """Evidence must come from this learner reply, never a hint or teacher text."""
    if not plan or plan["status"] != "active":
        return False
    phrase = result.get("phrase", {})
    text = phrase.get("text", "").strip()[:220]
    if text and len(plan["vocabulary"]) < 12 and normalized(text) not in {normalized(v["text"]) for v in plan["vocabulary"]}:
        plan["vocabulary"].append({"text": text, "translation": str(phrase.get("translation", ""))[:300],
                                   "english": str(phrase.get("english", ""))[:300], "base": base})
    objective = pending_objective(plan)
    evidence = result.get("objective_evidence")
    assessment = result.get("assessment") or {}
    if action != "reply" or not objective or not isinstance(evidence, dict):
        return False
    quote = evidence.get("quote", "")
    if (evidence.get("id") == objective["id"] and evidence.get("achieved") is True
            and isinstance(quote, str) and normalized(quote) and len(quote) <= 500
            and f" {normalized(quote)} " in f" {normalized(user_text)} "
            and assessment.get("verdict") in ("correct", "almost", "needs_work")
            and assessment.get("clarity") == "clear" and (assessment.get("rating") or 0) >= 3):
        objective.update(evidence=quote, turn=turn)
    return all(o["evidence"] for o in plan["objectives"])


def summary(plan):
    if not plan:
        return None
    return {"status": plan["status"], "achieved": sum(bool(o["evidence"]) for o in plan["objectives"]),
            "total": len(plan["objectives"]), "vocabulary_count": len(plan["vocabulary"])}


def completion_segment(target):
    text = {"it": "Ottimo lavoro! Abbiamo raggiunto tutti gli obiettivi della lezione. Puoi continuare a parlare o passare alla prossima lezione.",
            "fr": "Bravo ! Tous les objectifs de la leçon sont atteints. Vous pouvez continuer à discuter ou passer à la leçon suivante.",
            "en": "Well done! You have achieved every goal of this lesson. You can keep chatting or move on to the next lesson."}[target]
    return {"language": target, "kind": "instruction", "text": text}


def task_segment(plan, base):
    objective = pending_objective(plan)
    if not objective:
        return None
    prefix = "Prochaine étape : " if base == "fr" else "Your next task: "
    return {"language": base, "kind": "instruction", "text": prefix + objective[base] + "."}
