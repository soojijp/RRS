# 2. inject fake review/vote
# 	Input
# 		review 	<-- './intermediate/review.npy'
# 		vote 	<-- './intermediate/vote.npy'
# 	Output
# 		fake review 	--> './intermediate/fake_review_[average|bandwagon].npy'
# 		camo review 	--> './intermediate/camo_review_[average|bandwagon].npy'
# 		fake vote 		--> './intermediate/fake_vote_[average|bandwagon].npy'

import numpy as np
import csv
print("this is attack model bandwagon new!!!!!!!!!!!!!!!!!!")
class attack_model_bandwagon():
	def __init__(self, params=None):

		# num_fake_user=0.01, num_fake_item=0.01, num_camo_item=0.01 , num_fake_review=1, num_fake_vote=1, fake_rating_value=5, fake_helpful_value=5, badly_rated_item_flag=True
		# input
		self.review_origin_path = params.review_origin_path  #'./intermediate/review.npy'
		self.vote_origin_path = params.vote_origin_path  #'./intermediate/vote.npy'
		# output
		self.review_fake_path = params.review_fake_path  #'./intermediate/fake_review_bandwagon.npy'
		self.review_camo_path = params.review_camo_path  #'./intermediate/camo_review_bandwagon.npy'
		self.vote_fake_path = params.vote_fake_path  #'./intermediate/fake_vote_bandwagon.npy'
		self.vote_camo_path = params.vote_camo_path  #'./intermediate/camo_vote_bandwagon.npy'
		
		self.target_item_list_path = params.target_item_list_path
		self.fake_user_id_list_path = params.fake_user_id_list_path
		#######################################
		# origin review stats
		self.origin_review_matrix = np.load(self.review_origin_path)
		self.origin_vote_matrix = np.load(self.vote_origin_path)
		
		self.num_origin_user = len(np.unique(self.origin_review_matrix[:,0]))
		
		self.num_origin_item = len(np.unique(self.origin_review_matrix[:,1]))
		self.num_origin_review = len(self.origin_review_matrix)
		self.num_origin_vote = len(self.origin_vote_matrix)
		
		
		#######################################
		# # reading parameter 
		# attacker size param
		self.num_fake_user = int(self.num_origin_user*params.num_fake_user) if params.num_fake_user<=1 else int(params.num_fake_user)
		# camofoulage item size param
		self.filler_size = int(self.num_origin_item*params.filler_size) if params.filler_size <=1 else int(params.filler_size)
		self.selected_size = int(self.num_origin_item*params.selected_size) if params.selected_size <=1 else int(params.selected_size)
		
		# target item size param
		# self.num_fake_item = int(self.num_origin_item*params.num_fake_item) if params.num_fake_item<=1 else int(params.num_fake_item)
		self.num_fake_item = params.num_fake_item
		print '#(fake item)', self.num_fake_item
		
		# fake_rating value is usually extream value
		self.fake_rating_value = params.fake_rating_value
		self.fake_helpful_value = params.fake_helpful_value

		self.camo_vote_size_multiple = params.camo_vote_size_multiple
		# attack metadata param
		self.badly_rated_item_flag=params.badly_rated_item_flag
		self.bad_item_threshold = params.bad_item_threshold

		# injection stats
		self.fake_user_start = None
		self.fake_user_id_list = None
		self.fake_item_id_list = None

		self.fake_review_id_start = None
		self.num_fake_review = None
		self.fake_review_id_list = None # list(range(self.fake_review_id_start, self.fake_review_id_start+num_fake_review))

		self.camo_review_id_start = None # self.fake_review_id_start+self.num_fake_review
		
		self.avg_rating_list = None

		self.fake_review_writer = dict()

		# output data
		self.fake_review_matrix = None
		self.camo_review_matrix = None
		self.fake_vote_matrix = None
		self.camo_vote_matrix = None

	# for target item
	def get_bad_items_info(self,topk=10, threshold=0, random_flag=False):
		# many bad rating
		item_score = dict()
		for row in self.origin_review_matrix:
			item_id = row[1]
			rating = float(row[2])
			if item_id not in item_score:
				item_score[item_id]=[0,0]
			item_score[item_id][0]+=rating
			item_score[item_id][1]+=1

		item_score_list = []
		for k in item_score.keys():
			# item_id, overall rating, the number of rating
			item_score_list.append([k, item_score[k][0]/float(item_score[k][1]), item_score[k][1]])

		item_score_list = sorted(item_score_list, key=lambda x:x[1])
		# item_score_list = filter(lambda x: x[1]<3 and x[2]>=threshold, item_score_list)
		item_score_list = filter(lambda x: x[1]<4 and x[2]>=threshold, item_score_list)
		
		# 3 cut-> 8 / 3.5 cut -> 51 / 4 cut -> 181
		# print len(item_score_list), item_score_list
		
		if random_flag:
			random_index_list = np.random.choice(a=len(item_score_list), size=topk, replace=False)
			return [item_score_list[idx] for idx in random_index_list]
		else:
			return item_score_list[0:topk]
	
	# for average attack
	def construct_avg_rating(self):
		sum_rating_ist = np.zeros((self.num_origin_item,))
		num_rating_list = np.zeros((self.num_origin_item,))
		for row in self.origin_review_matrix:
			item_id = int(row[1])
			rating = float(row[2])
			sum_rating_ist[item_id]+=rating
			num_rating_list[item_id]+=1.0
		self.avg_rating_list = sum_rating_ist/num_rating_list
	
	# for bandwagon attack
	def get_popular_item(self, topk=10):
		from collections import Counter
		a = self.origin_review_matrix[:,1]
		b = Counter(a)
		# [(item_id, occurence)*]
		# [(944, 212), (912, 156), (1436, 135), (2277, 126), (2577, 124), (2797, 115)]
		return b.most_common(topk)

	############
	## REVIEW ##
	############
	def inject_attack_reviews(self):
		self.fake_user_start = self.num_origin_user  # new users are injected 
		self.fake_user_id_list = list(range(self.fake_user_start, self.fake_user_start+self.num_fake_user))
		self.fake_review_id_start = self.num_origin_review # new reviews are injected
		self.generate_fake_reviews()
		
		self.camo_review_id_start = self.fake_review_id_start+self.num_fake_review
		self.generate_camo_reviews()
	
	# inject (fake user, target item, maximum item rating value)
	def generate_fake_reviews(self):
		self.fake_review_matrix = []

		# target items are badly rated items
		bad_item_info_list = self.get_bad_items_info(self.num_fake_item, threshold=self.bad_item_threshold)
		# print 'bad_item_info_list', bad_item_info_list
		self.fake_item_id_list = [x[0] for x in bad_item_info_list]

		fake_review_id = self.fake_review_id_start
		for fake_u in self.fake_user_id_list:
			for fake_i in self.fake_item_id_list:
				self.fake_review_matrix.append([fake_u, fake_i, self.fake_rating_value, fake_review_id])
				self.fake_review_writer[fake_review_id]=fake_u
				fake_review_id+=1
		self.num_fake_review = len(self.fake_review_matrix)
	
	# inject (fake user, filler item, average item rating value), (fake user, popular item, maximum item rating value)
	def generate_camo_reviews(self):
		self.camo_review_matrix = []

		camo_review_id = self.camo_review_id_start
		# random attack
		for u in self.fake_user_id_list:
			random_item_list = np.random.choice(a=self.num_origin_item, size=self.filler_size)
			for i in random_item_list:
				tmp_random_review = [u, i, int(np.round(self.avg_rating_list[i])), camo_review_id]
				self.camo_review_matrix.append(tmp_random_review)
				camo_review_id+=1

		# popular attack (bandwagon attack)
		popular_item_list = self.get_popular_item(self.selected_size)
		popular_item_list = [x[0] for x in popular_item_list]
		# print('camo item list', popular_item_list)
		for u in self.fake_user_id_list:
			for i in popular_item_list:
				self.camo_review_matrix.append([u,i,5,camo_review_id])
				camo_review_id+=1
	
	##################
	###### VOTE ######
	##################
	def inject_attack_votes(self):
		self.fake_review_id_list = list(range(self.fake_review_id_start, self.fake_review_id_start+self.num_fake_review))

		self.generate_fake_votes()
		self.generate_camo_votes()

	def generate_fake_votes(self):
		self.fake_vote_matrix = []
		for fake_u in self.fake_user_id_list:
			for fake_r in self.fake_review_id_list:
				# can give helpfulness rating only to the reviews of other users
				if fake_u != self.fake_review_writer[fake_r]:
					self.fake_vote_matrix.append([fake_u,fake_r, self.fake_helpful_value])

	def generate_camo_votes(self):
		self.camo_vote_matrix = []
		camo_vote_size = int(self.camo_vote_size_multiple*(len(self.fake_review_id_list)-len(self.fake_item_id_list)))
		print '[generate_camo_votes] each user camo_vote_size', camo_vote_size
		for fake_u in self.fake_user_id_list:
			camo_r_list = np.random.choice(a=self.num_origin_review, size=camo_vote_size, replace=False)
			for camo_r in camo_r_list:
				self.camo_vote_matrix.append([fake_u,camo_r, int(np.random.choice(a=list(range(6)),size=1))])



	def save_attack_review_matrix(self):
		np.save(self.review_fake_path, np.array(self.fake_review_matrix))
		np.save(self.review_camo_path, np.array(self.camo_review_matrix))

	def save_attack_vote_matrix(self):
		np.save(self.vote_fake_path, np.array(self.fake_vote_matrix))
		np.save(self.vote_camo_path, np.array(self.camo_vote_matrix))

	def save_fake_user_id_list(self):
		fake_review_matrix_ = np.array(self.fake_review_matrix)
		np.save(self.fake_user_id_list_path, np.unique(fake_review_matrix_[:,0]))

	def save_target_item_list(self):
		fake_review_matrix_ = np.array(self.fake_review_matrix)
		np.save(self.target_item_list_path, np.unique(fake_review_matrix_[:,1]))

	def whole_process(self):
		self.construct_avg_rating()

		# review
		self.inject_attack_reviews()
		self.save_attack_review_matrix()

		# vote
		self.inject_attack_votes()
		self.save_attack_vote_matrix()

		# save the metadata of attack
		self.save_fake_user_id_list()
		self.save_target_item_list()

		print '[Origin stats] Users x Items:', self.num_origin_user, self.num_origin_item
		print '[Attack stats] Sybil size:', self.num_fake_user, 'Target size, Filler size, Selected size:', len(self.fake_item_id_list), self.filler_size, self.selected_size
		
		print '[Origin] Reviews, Votes:', self.num_origin_review, self.num_origin_vote
		print '[ Fake ] Reviews, Votes:',len(self.fake_review_matrix), len(self.fake_vote_matrix)
		print '[ Camo ] Reviews, Votes:',len(self.camo_review_matrix), len(self.camo_vote_matrix)

if __name__=="__main__":
	pass
	# from parameter_controller import *
	# exp_title = 'bandwagon_1%_1%_1%_emb_32'
	# print('Experiment Title', exp_title)
	# params = parse_exp_title(exp_title)
	# am = attack_model_bandwagon(params=params)
	# am.whole_process()
