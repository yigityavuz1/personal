from nltk import word_tokenize
import textdistance
import pandas as pd


def fix_with_sim_levenshtein(content, key):
    # result = []
    # result_score = []
    if key == "":
        return "", 0
    else:
        content_tokens = word_tokenize(content)
        CONTENT_LEN = len(content_tokens)
        KEY_LEN = len(key.split(" "))
        max = 0
        max_PART = ""
        for i in range(CONTENT_LEN):
            for offset in range(-1, 2):
                PART = " ".join(content_tokens[i:i + KEY_LEN + offset])
                levenshtein = textdistance.levenshtein.normalized_similarity(key, PART)
                if levenshtein > max:
                    max = levenshtein
                    max_PART = PART
    return max_PART, max


df = pd.read_excel('../data/ayrimci_dil_sozluk_v3.xlsx')
filtered_df = df[df['Kullanım Alanı'] == 'İş İlanı']
ALL_KEYWORDS = [i.strip() for i in filtered_df['Ayrımcı Dil İçeren Kelime'].values.tolist()]

context = """
Pozisyonun Amacı: Sorumlu olunan bayilerin il bazında pazar paylarını artırmak, şirket KPI’larına öncelik vererek bayi karlılıkları, müşteri memnuniyetini artırmak. Marka değerini artırmak adına, bayilerin gelecek yıllardaki rekabete hazırlanmalarını sağlamak. İş sonuçlarına göre bayilere danışmanlık yapmak. Düşük performans gösteren bayileri iyileştirme çalışmaları gerçekleştirmek, gereken şartların oluşması durumunda yeniden yapılanma konusundaki çalışmalara destek vermek. Sorumluluklar Bölgesindeki bayilerin satış hedeflerini en az %100 ve daha fazla baremlerde gerçekleşmelerini sağlamak. Oto ve LCV Pazar paylarını inceleyerek sorumlu olduğu iller bazında Pazar lideri olmak için gerekli çalışmaları düzenlemek. Müşteri Memnuniyet skorlarını geliştirmek. Yerel Pazarlama ve digital pazarlama uygulamalarını bölge bayilerinde etkin bir şekilde kullanılmasını koordine etmek.Kendisine bağlı bayilerin Satış Müdürlerinin gelişimini desteklemek ve onların başarılı sonuçlar alması için koçvari liderlik yapmak.Marka standartlarını temsil noktalarında uygulamak için gerekli önlemleri almak. Her çeyrekte standartların denetimini gerçekleştirmek. Satış sonrası ve yedek parça direktörlüğü ile işbirliği geliştirerek, bayilerin gelişimlerini sürekli kılmak.
Üniversitelerin Lisans bölümlerinden mezun olmak, Minimum üst orta düzeyde İtalyanca ve/veya İngilizce bilgisine sahip olmak, MS Ofis programlarını etkin olarak kullanmak, Satış ve saha yönetimi konusunda en az 3 yıl tecrübe sahibi olmak, Otomotiv sektöründe en az 3 yıl çalışmak olmak. Ayrıca; dış görünümüne dikkat etmesi, Seyahat engelinin olmaması, 30 yaşın altında olan, Mevcut şirket kültürü ve yönetim prensipleri ile markamızı en iyi şekilde dışarda temsil becerisi, İlişki yönetimi, Uyum içinde çalışma ve uzlaşı kültürü, Sonuç Odaklılık, hırslı ve kendinden emin olması, Beklenen diğer yetkinlikler arası
"""
keywords = []
for key in ALL_KEYWORDS:
    part, score = fix_with_sim_levenshtein(context, key)
    if score > 0.6:
        print(key, ":", part, score)
