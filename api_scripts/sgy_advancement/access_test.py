from requests_oauthlib import OAuth1Session


def main():
    test = OAuth1Session(
        'aaa649f9fabadf81def11f492db08420064aad79a',
        client_secret='6b4a5b3bc85b7d0fe719e8465ee87661'
    )
    url = 'https://api.schoology.com/v1/sections/2316722634/assignments/5811649137'
    r = test.get(url)
    print(r.content)


if __name__ == '__main__':
    main()
