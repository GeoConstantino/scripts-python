import os
import pytest
import responses
import re
import shutil
from bs4 import BeautifulSoup
from downloader.main import LrfDownloader, USER_AGENT
from unittest import TestCase
from .fixtures import (
    index,
    cities,
    results,
    links
)


class DownloaderTest(TestCase):
    @responses.activate
    def setUp(self):
        responses.add(
            'GET',
            LrfDownloader._base_address,
            body=index
        )
        downloader = LrfDownloader(2013)
        self.downloader = downloader
        self.downloader.initiate()

    def tearDown(self):
        if os.path.exists('output'):
            shutil.rmtree('output')

    def test_initial_year(self):
        assert self.downloader.initial_year == 2013

    @responses.activate
    def test_get_session(self):
        assert self.downloader.session is not None
        assert self.downloader.session.headers['user-agent'] == USER_AGENT

    @responses.activate
    def test_get_initiate(self):
        assert self.downloader.cities == cities

    @responses.activate
    def test_get_initiate_status_fail(self):
        responses.add(
            'GET',
            LrfDownloader._base_address,
            body='',
            status=500
        )

        with pytest.raises(Exception) as error:
            self.downloader.initiate()
        
        assert 'Response malformed with status code 500' == str(error.value)

    def test_parse_links(self):
        assert self.downloader._parse_download_table(
            BeautifulSoup(results, 'lxml')
        ) == links

    @responses.activate
    def test_get_city_data(self):
        responses.add(
            'POST',
            LrfDownloader._base_address,
            body=results
        )

        parameters = {
            'MunicipioID': 6,
            'Ano': 2013
        }

        result = self.downloader._get_city_data(
            6,
            2013
        )

        requested_parameters = responses.calls[0].request.body

        assert result == links
        assert requested_parameters == 'MunicipioID=6&Ano=2013'
    
    @responses.activate
    def test_download_pdfs(self):
        responses.add(
            'GET',
            re.compile(
                f'{self.downloader._root_address}/portlet-responsabilidadefiscal/responsabilidadefiscal/GetArquivo.+'
            ),
            body='lerolero'
        )
        
        self.downloader._download_pdfs(
            'Rio Branco',
            '2016',
            links
        )

        assert len(responses.calls) == 117
        assert responses.calls[0].request.url == 'https://www.tce.rj.gov.br/portlet-responsabilidadefiscal/responsabilidadefiscal/GetArquivo?tipoAnexo=RREO12&orgaoID=771&Ano=2013&Mes=2&recebimento=07%2F16%2F2013%2012%3A40%3A27'

    def test_save_pdf(self):
        self.downloader._save_pdf('a weird district', 2014, '11/10/2014', 'a realy wéird filename', b'lerolerolalala')

        assert os.path.exists('output/a-weird-district/2014/a-realy-weird-filename-20141011.pdf')
