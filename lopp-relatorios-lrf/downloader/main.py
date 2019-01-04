import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from slug import slug
from tqdm import tqdm


USER_AGENT = ('Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/'
              '4.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET '
              'CLR 3.5.30729; .NET CLR 2.0.50727)')


class RequestError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(
            f"Response malformed with status code {args[0]}",
            *args[1:],
            **kwargs)


class LrfDownloader:
    _base_address = ('https://www.tce.rj.gov.br/'
                     'portlet-responsabilidadefiscal/responsabilidadefiscal')
    _root_address = 'https://www.tce.rj.gov.br'

    def __init__(self, initial_year):
        self.session = self._get_session()
        self.initial_year = initial_year
        self.cities = None

    def _get_session(self):
        'Prepares a requests session with suitable headers'
        session = requests.Session()
        session.headers.update({'user-agent': USER_AGENT})
        return session

    def _parse_cities(self, soup):
        'Parse cities from the base page for post iteration'
        cities_select = soup.find(id='MunicipioID')
        return [
            (option.attrs['value'], option.text.strip())
            for option in cities_select.find_all(
                'option',
                {'value': re.compile(r'\d+')}
            )
        ]

    def initiate(self):
        'Performs initial request to prepare cookies and get district'
        response = self.session.get(self._base_address)
        if response.status_code != 200:
            raise RequestError(response.status_code)

        self.cities = self._parse_cities(
            BeautifulSoup(response.content, 'lxml')
        )

    def _parse_download_table(self, soup):
        'Parses all download links for PDFs'
        table = soup.findAll('table')[1]

        # skip th
        links = []
        for line in table.findAll('tr')[1:]:
            line = line.findAll('td')
            relese = line[-3].text.strip()
            name = line[-2].text.strip()
            link = line[-1].find('a').attrs['href']
            links.append(
                (relese, name, link)
            )

        return links

    def _get_city_data(self, city_id, year):
        'Requests and parses city links'
        response = self.session.post(
            self._base_address,
            data={
                'MunicipioID': city_id,
                'Ano': year
            }
        )

        if response.status_code != 200:
            raise RequestError(response.status_code)

        return self._parse_download_table(
            BeautifulSoup(response.content, 'lxml')
        )

    def _save_pdf(self, district, year, release, filename, bcontent):
        'saves a pdf to disk'
        district = slug(district)
        filename = slug(filename)
        release = release.strip().split('/')
        release.reverse()
        release = slug(''.join(list(release)))
        os.makedirs(f'output/{district}/{year}', exist_ok=True)
        with open(
                f'output/{district}/{year}/{filename}-{release}.pdf',
                'wb') as file:
            file.write(bcontent)

    def _download_pdf(self, address):
        'downloads a pdf from the server'
        response = self.session.get(f'{self._root_address}{address}')
        if response.status_code != 200:
            raise RequestError(response.status_code)

        return response.content

    def _download_pdfs(self, district, year, links):
        'for a link list, download all its pdfs and save to disk'
        for pdf_row in tqdm(links, unit='pdf', desc=f"Year: {year}"):
            content = self._download_pdf(pdf_row[-1])

            self._save_pdf(
                district,
                year,
                pdf_row[-3],
                pdf_row[-2],
                content
            )

    def _download_city_pdfs(self, city):
        for year in tqdm(
                    range(self.initial_year, datetime.now().year+1),
                    unit='year',
                    desc=f"Scrapping {city[1]}"
                ):
            links = self._get_city_data(city[0], year)

            self._download_pdfs(
                city[1],
                year,
                links
            )

    def scrap_cities(self):
        for city in tqdm(
                self.cities,
                unit='city',
                desc='Scrapping Cities'):

            self._download_city_pdfs(city)


if __name__ == '__main__':
    downloader = LrfDownloader(2013)
    downloader.initiate()
    downloader.scrap_cities()
