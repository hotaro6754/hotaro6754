"""Stopword lists for explainable topic extraction.

Chats mix languages and scripts freely. A recurring-topic list made of
pronouns, particles and forms of address ("raa", "anna", "haan") tells the
reader nothing, so those are excluded. The lists below are hand-curated,
visible and meant to be extended; each line is one group.
"""

ENGLISH = """
a about above after again against all also am an and any are aren't as at be because been before being
below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down
during each few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here
here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself
let's me more most mustn't my myself no nor not of off on once only or other ought our ours ourselves
out over own same shan't she she'd she'll she's should shouldn't so some such than that that's the their
theirs them themselves then there there's these they they'd they'll they're they've this those through
to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's
where where's which while who who's whom why why's with won't would wouldn't you you'd you'll you're
you've your yours yourself yourselves
im ive id dont didnt doesnt cant wont isnt thats whats youre ill
"""

CHAT_FILLER = """
just like get got go going gonna wanna will would one also really much still even well now then today
tomorrow yesterday tonight time know think want need make see say said tell told come came take back
yes yeah yep yup yea ya nope nah ok okay okk okie k kk sure fine good great nice cool right alright
haha hahaha hehe lol lmao rofl hmm hmmm hm ohh oh ooh ah ahh uh um umm wow omg bro dude man yaar
hi hii hey hello bye thanks thank thx tq ty pls plz please sorry welcome morning night gn gm
u ur r n y pic pics msg msgs text full start send sent wait first last use real min nahh
true let agreed done makes sense definitely way check call free busy reached thing things something
anything maybe actually literally though already bit lot guess thats there's yours mine
"""

# Strings WhatsApp itself writes into exports.
WHATSAPP = """
media omitted message deleted edited attached image video audio sticker gif document null
live location shared
"""

# Romanised Telugu: pronouns, particles, auxiliaries and forms of address.
TELUGU = """
ra raa re rey ey ay oy anna akka bava mama macha babu amma nana
ha haa haan nen nenu naa na naku naaku nannu nanu nuv nuvvu nee ne neeku neku ninnu nu mee meeru meeku
memu manam manaki vaadu vadu vaadi vadi aame ame adhi adi idhi idi avi ivi aa ee
undhi undi unnadi unnav unnava unna unnanu ledhu ledu leda ledha kaadu kadu kaadhu kada kadha
emo emi enti endhi endi enduku endhuku ela ekkada eppudu evaru evadu evari entha
oka okka okati chey cheyi chesa chesav chesava chesanu cheyali chestha chestunna chepu cheppu chepa
chepta cheppa cheppara pettu pettara ochi vachi vachav vasta vastha osta poyi po pora povali
kuda kooda inka inkaa ippudu appudu sare sari avunu avnu ante antey kani kaani matram ga gaa ki ku ni
lo tho nundi varaku ani anni chala chaala baga em emaindi emaindhi telusu teliyadu ayindhi ayindi
kavali kaavali
yo yoo daa repu andhuke antha ala ayina kadhu mari malli ayithe aithe ante enti anukunta
"""

# Romanised Hindi.
HINDI = """
hai hain ho tha thi the kya kyu kyun nahi nahin nhi mat han ji to toh bhi bhai abe arey arre accha acha
thik theek kar karo karna kiya kiye raha rahi rahe hoga hogi mera meri mere tera teri tere tum tu aap
hum main mai mujhe tujhe apna apni wo woh vo ye yeh is us iska uska kuch sab bas abhi phir fir kab
kaise kaun kaha kahan ka ke ko se mein me pe par ne
"""

# Romanised Tamil (a starter set).
TAMIL = """
da di dei enna illa irukku vaa naan avan aval
"""

STOPWORDS = frozenset(
    w for block in (ENGLISH, CHAT_FILLER, WHATSAPP, TELUGU, HINDI, TAMIL) for w in block.split()
)
