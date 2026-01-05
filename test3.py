import sys
import time
import jwt

# Open PEM
private_key = """-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEINxwIZW05/wkglYtxNlXmYElLhxwQ5XCGWPoGHmUr5C8
-----END PRIVATE KEY-----"""

payload = {
    'iat': int(time.time()) - 30,
    'exp': int(time.time()) + 900,
    'sub': '4E88355UX6'
}
headers = {
    'kid': 'C5PU3VEWJ3'
}

# Generate JWT
encoded_jwt = jwt.encode(payload, private_key, algorithm='EdDSA', headers = headers)

print(f"JWT:  {encoded_jwt}")
eyJhbGciOiJFZERTQSIsImtpZCI6IkM1UFUzVkVXSjMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NjczMjQ0MDgsImV4cCI6MTc2NzMyNTMzOCwic3ViIjoiNEU4ODM1NVVYNiJ9.8tKSkKyXIH81PgtAORP9Gvmdu8ELvjAEwGjpmoBqT9gADz41nox1Ze5qs5uw_oWXHHro2_XIFILr4CY6W2FsDg


test = {
    "code":"200",
    "location":
        [
            {
                "name":"株洲",
                "id":"101250301",
                "lat":"27.83581",
                "lon":"113.15173",
                "adm2":"株洲",
                "adm1":"湖南省",
                "country":"中国",
                "tz":"Asia/Shanghai",
                "utcOffset":"+08:00",
                "isDst":"0",
                "type":"city",
                "rank":"15",
                "fxLink":"https://www.qweather.com/weather/zhuzhou-101250301.html"
            },
            {
                "name":"荷塘",
                "id":"101250304",
                "lat":"27.83304",
                "lon":"113.16254",
                "adm2":"株洲",
                "adm1":"湖南省",
                "country":"中国",
                "tz":"Asia/Shanghai",
                "utcOffset":"+08:00",
                "isDst":"0",
                "type":"city",
                "rank":"35",
                "fxLink":"https://www.qweather.com/weather/hetang-101250304.html"
            },
            {
                "name":"芦淞",
                "id":"101250307",
                "lat":"27.82725",
                "lon":"113.15517",
                "adm2":"株洲",
                "adm1":"湖南省",
                "country":"中国",
                "tz":"Asia/Shanghai",
                "utcOffset":"+08:00",
                "isDst":"0",
                "type":"city",
                "rank":"45",
                "fxLink":"https://www.qweather.com/weather/lusong-101250307.html"
            },
            {
                "name":"石峰",
                "id":"101250308",
                "lat":"27.87194",
                "lon":"113.11295",
                "adm2":"株洲",
                "adm1":"湖南省",
                "country":"中国",
                "tz":"Asia/Shanghai",
                "utcOffset":"+08:00",
                "isDst":"0",
                "type":"city",
                "rank":"35",
                "fxLink":"https://www.qweather.com/weather/shifeng-101250308.html"
            },
            {
                "name":"天元",
                "id":"101250309",
                "lat":"27.82674",
                "lon":"113.08223",
                "adm2":"株洲",
                "adm1":"湖南省",
                "country":"中国",
                "tz":"Asia/Shanghai",
                "utcOffset":"+08:00",
                "isDst":"0",
                "type":"city",
                "rank":"45",
                "fxLink":"https://www.qweather.com/weather/tianyuan-101250309.html"
            },
            {
                "name":"攸县","id":"101250302","lat":"27.01516","lon":"113.39715","adm2":"株洲",
                "adm1":"湖南省","country":"中国","tz":"Asia/Shanghai","utcOffset":"+08:00",
                "isDst":"0","type":"city","rank":"33",
                "fxLink":"https://www.qweather.com/weather/you-county-101250302.html"
            },
            {
                "name":"醴陵","id":"101250303","lat":"27.65787","lon":"113.50716","adm2":"株洲","adm1":"湖南省",
                "country":"中国","tz":"Asia/Shanghai","utcOffset":"+08:00","isDst":"0","type":"city","rank":"23",
                "fxLink":"https://www.qweather.com/weather/liling-101250303.html"
            },
            {
                "name":"茶陵","id":"101250305","lat":"26.78953","lon":"113.54651","adm2":"株洲","adm1":"湖南省",
                "country":"中国","tz":"Asia/Shanghai","utcOffset":"+08:00","isDst":"0","type":"city","rank":"33",
                "fxLink":"https://www.qweather.com/weather/chaling-101250305.html"
            },
            {
                "name":"炎陵","id":"101250306","lat":"26.48946","lon":"113.77689","adm2":"株洲","adm1":"湖南省",
                "country":"中国","tz":"Asia/Shanghai","utcOffset":"+08:00","isDst":"0","type":"city","rank":"45",
                "fxLink":"https://www.qweather.com/weather/yanling-101250306.html"
            },
            {
                "name":"渌口","id":"101250310","lat":"27.69936","lon":"113.14383","adm2":"株洲","adm1":"湖南省",
                "country":"中国","tz":"Asia/Shanghai","utcOffset":"+08:00","isDst":"0","type":"city","rank":"40",
                "fxLink":"https://www.qweather.com/weather/lukou-101250310.html"
            }
        ],
    "refer":
        {
            "sources":["QWeather"],
            "license":["QWeather Developers License"]
        }
}