import unittest
from experience_validation import normalize_experience
class ExperienceForms(unittest.TestCase):
 def save(self,group,data):
  return normalize_experience({'fromStageGroup':group},{'experience':data})
 def test_start_stage_owns_form(self):
  self.assertEqual(self.save('TEST',{'notes':'测试复盘','kind':'OFFER_CALL'})['kind'],'TEST')
  offer=self.save('OFFER_CALL',{'initialOffer':'1. 月薪 **20k**','negotiatedOffer':'1. 增加签字费'})
  self.assertIn('签字费',offer['summary'])
 def test_solo_boundaries_and_group_hidden_count(self):
  for count in (1,20):
   result=self.save('INTERVIEW',{'interviewType':'SOLO','candidateCount':count,'questions':'1. 介绍项目'})
   self.assertEqual(result['candidateCount'],count)
  for count in (0,21,1.5,True,'2'):
   with self.assertRaises(ValueError):self.save('INTERVIEW',{'interviewType':'SOLO','candidateCount':count,'other':'复盘'})
  group=self.save('INTERVIEW',{'interviewType':'GROUP','candidateCount':9,'other':'讨论分工'})
  self.assertNotIn('candidateCount',group)
 def test_empty_and_ineligible(self):
  for group,data in [('TEST',{'notes':''}),('INTERVIEW',{'interviewType':'SOLO','candidateCount':1,'questions':'1. '}),('OFFER_CALL',{'initialOffer':'1. ','negotiatedOffer':'1. '}),('RESUME',{'notes':'记录'})]:
   with self.assertRaises(ValueError):self.save(group,data)
 def test_legacy_preserved(self):
  self.assertEqual(normalize_experience({'fromStage':'TEST'},{'summary':'旧笔记'})['summary'],'旧笔记')
if __name__=='__main__':unittest.main()
