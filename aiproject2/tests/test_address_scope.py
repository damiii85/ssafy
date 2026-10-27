import unittest
from unittest.mock import patch

import pandas as pd

from src.services.chat_controller import answer_question
from src.services.distance_scope import scoped_stores
from src.services.address_scope import resolve_address
from src.services.location_analyzer import calculate_distance
from src.services.pilot_report import load_spot_data


class AddressScopeTests(unittest.TestCase):
    def setUp(self):
        self.stores, self.meta = load_spot_data('daegu_downtown')

    def ask(self, text, state=None):
        return answer_question('daegu_downtown', text, {} if state is None else state,
                               self.stores, self.meta, 1000)

    def test_address_100m_matches_actual_coordinate_filter(self):
        question = '대구광역시 중구 중앙대로 412-21 기준 100m 카페'
        location = resolve_address(question, 'daegu_downtown', self.stores)
        answer, report = self.ask(question)
        nearby = self.stores.loc[[calculate_distance(location['latitude'], location['longitude'], r.lat, r.lon) <= 100 + 1e-6
                                  for r in self.stores.itertuples()]]
        self.assertEqual(report['total_stores'], len(nearby))
        self.assertEqual(report['competitor_count'], int((nearby.indsSclsNm == '카페').sum()))
        self.assertEqual(report['scope_latitude'], location['latitude'])
        self.assertNotEqual(report['scope_latitude'], self.meta['center_lat'])
        self.assertIn('중앙대로 412-21', answer)
        self.assertIn('위치 출처', report['scope_description'])

    def test_address_changes_followup_and_reset(self):
        state = {}
        _, first = self.ask('중앙대로 412-21 100미터 카페', state)
        _, second = self.ask('200m 이내는?', state)
        self.assertEqual(first['scope_latitude'], second['scope_latitude'])
        self.assertEqual(second['radius_m'], 200)
        _, moved = self.ask('종로 46-2 카페', state)
        self.assertIn('종로 46-2', moved['scope_center'])
        self.assertEqual(moved['radius_m'], 200)
        self.assertNotEqual(moved['scope_longitude'], second['scope_longitude'])
        _, full = self.ask('지역 전체 카페 현황', state)
        self.assertEqual(full['total_stores'], len(self.stores))
        self.assertNotIn('address_location', state)

    def test_address_then_industry_uses_saved_address_radius(self):
        state = {}
        text, report = self.ask('중앙대로 412-21 100m', state)
        self.assertIsNone(report)
        self.assertIn('입력한 주소', text)
        _, report = self.ask('카페', state)
        self.assertIn('412-21', report['scope_center'])
        self.assertEqual(report['radius_m'], 100)

    def test_unknown_multiple_outside_address_never_uses_anchor(self):
        state = {}
        self.ask('중앙대로 412-21 100m 카페',state)
        _,report=self.ask('서울 중구 중앙대로 412-21 100m 카페',state)
        self.assertIsNone(report)
        _,report=self.ask('100m 이내는?',state)
        self.assertIsNone(report)
        for question in ['없는길 99999 100m 카페', '서울 중구 중앙대로 412-21 카페',
                         '중앙대로 412-21과 종로 46-2 100m 카페']:
            text, report = self.ask(question, state)
            self.assertIsNone(report, text)
        text, report = self.ask('100m 카페', state)
        self.assertIsNone(report)
        self.assertIn('주소', text)

    def test_same_road_in_different_district_requires_disambiguation(self):
        frame = pd.DataFrame({'rdnmAdr':['대구광역시 중구 검증로 1','대구광역시 북구 검증로 1'],
                              'lat':[35.87,35.88], 'lon':[128.59,128.6]})
        with patch('src.services.address_scope.load_spots',return_value=[]):
            with self.assertRaises(ValueError):
                resolve_address('검증로 1 100m 카페','daegu_downtown',frame)
            self.assertIn('중구',resolve_address('대구 중구 검증로 1 100m 카페','daegu_downtown',frame)['address'])

    def test_shifted_address_circle_must_be_covered(self):
        location={'latitude':self.meta['center_lat']+.1,'longitude':self.meta['center_lon'],'address':'확인 주소'}
        with self.assertRaises(ValueError):
            scoped_stores('daegu_downtown',self.stores,self.meta,'100m',{},location)

    def test_road_number_does_not_match_another_building(self):
        with patch('src.services.address_scope.load_spots',return_value=[]):
            with self.assertRaises(ValueError):
                resolve_address('검증로 12 100m 카페','daegu_downtown',pd.DataFrame({'rdnmAdr':['대구 중구 검증로 123'],'lat':[35.87],'lon':[128.59]}))
        self.assertIsNone(resolve_address('동성로 100m 카페','daegu_downtown',self.stores))
        with patch('src.services.address_scope.load_spots',return_value=[]):
            frame = pd.DataFrame({'rdnmAdr':['대구 중구 동성로2길 5'],'lat':[35.87],'lon':[128.59]})
            self.assertEqual(resolve_address('동성로 2길 5 100m 카페','daegu_downtown',frame)['address'],'대구 중구 동성로2길 5')
