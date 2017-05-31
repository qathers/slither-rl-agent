import os

import gym
import universe

import numpy as np
import tensorflow as tf
import tensorflow.contrib.layers as layers

class Network(object):
	def __init__(self, FLAGS):
		self.FLAGS = FLAGS
		self.num_actions = FLAGS.num_actions
		self.img_height, self.img_width, self.img_depth = FLAGS.state_size

	def build(self):
		self.scope = "scope"
		self.target_scope = "target_scope"

		self.add_placeholders_op()

		self.proc_s = self.process_state(self.s)
		self.proc_sp = self.process_state(self.sp)

		self.add_loss_op()

		self.add_update_target_op()

		self.add_optimizer_op()

	def initialize(self):
		self.sess = tf.Session()

		# tensorboard stuff
		self.add_summary()

		# initiliaze all variables
		self.sess.run(tf.global_variables_initializer())

		# synchronise q and target_q network
		self.update_target_params()

		# for saving network weights
		self.saver = tf.train.Saver()

	def get_best_action(self, state):
		action_values = self.sess.run(self.q, feed_dict={self.s: [state]})[0]
		return np.argmax(action_values), action_values

	def update_target_params(self):
		self.sess.run(self.update_target_op)

	def save(self):
		if not os.path.exists(self.FLAGS.model_path):
			os.makedirs(self.FLAGS.model_path)
		self.saver.save(self.sess, self.FLAGS.model_path)

	def add_placeholders_op(self):
		self.s = tf.placeholder(tf.uint8, [None, self.img_height, self.img_width, self.img_depth*self.FLAGS.state_hist])
		self.a = tf.placeholder(tf.int32, [None])
		self.r = tf.placeholder(tf.float32, [None])
		self.sp = tf.placeholder(tf.uint8, [None, self.img_height, self.img_width, self.img_depth*self.FLAGS.state_hist])
		self.done_mask = tf.placeholder(tf.bool, [None])
		self.lr = tf.placeholder(tf.float32, [])

	def add_update_target_op(self):
		scope_col = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope=self.scope)
		target_scop_col = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope=self.target_scope)

		assn_vec = []
		for i,var in enumerate(scope_col):
			assign = tf.assign(target_scop_col[i], scope_col[i])
			assn_vec.append(assign)

		self.update_target_op = tf.group(*assn_vec)

	def update_step(self, t, replay_buffer, lr):
		s_batch, a_batch, r_batch, sp_batch, done_mask_batch = replay_buffer.sample(self.FLAGS.batch_size)

		fd = {
			# inputs
			self.s: s_batch,
			self.a: a_batch,
			self.r: r_batch,
			self.sp: sp_batch, 
			self.done_mask: done_mask_batch,
			self.lr: lr, 
			# extra info
			self.avg_reward_placeholder: self.avg_reward, 
			self.max_reward_placeholder: self.max_reward, 
			self.std_reward_placeholder: self.std_reward, 
			self.avg_q_placeholder: self.avg_q, 
			self.max_q_placeholder: self.max_q, 
			self.std_q_placeholder: self.std_q, 
			self.eval_reward_placeholder: self.eval_reward, 
		}

		output_list = [self.loss, self.grad_norm, self.merged, self.train_op]
		loss_eval, grad_norm_eval, summary, _ = self.sess.run(output_list, feed_dict=fd)

		# tensorboard stuff
		self.file_writer.add_summary(summary, t)
		
		return loss_eval, grad_norm_eval

	def process_state(self, state):
		state = tf.cast(state, tf.float32)
		state /= self.FLAGS.high_val
		return state

	def add_summary(self):
		# extra placeholders to log stuff from python
		self.avg_reward_placeholder = tf.placeholder(tf.float32, shape=(), name="avg_reward")
		self.max_reward_placeholder = tf.placeholder(tf.float32, shape=(), name="max_reward")
		self.std_reward_placeholder = tf.placeholder(tf.float32, shape=(), name="std_reward")

		self.avg_q_placeholder  = tf.placeholder(tf.float32, shape=(), name="avg_q")
		self.max_q_placeholder  = tf.placeholder(tf.float32, shape=(), name="max_q")
		self.std_q_placeholder  = tf.placeholder(tf.float32, shape=(), name="std_q")

		self.eval_reward_placeholder = tf.placeholder(tf.float32, shape=(), name="eval_reward")

		# add placeholders from the graph
		tf.summary.scalar("loss", self.loss)
		tf.summary.scalar("grads norm", self.grad_norm)

		# extra summaries from python -> placeholders
		tf.summary.scalar("Avg Reward", self.avg_reward_placeholder)
		tf.summary.scalar("Max Reward", self.max_reward_placeholder)
		tf.summary.scalar("Std Reward", self.std_reward_placeholder)

		tf.summary.scalar("Avg Q", self.avg_q_placeholder)
		tf.summary.scalar("Max Q", self.max_q_placeholder)
		tf.summary.scalar("Std Q", self.std_q_placeholder)

		tf.summary.scalar("Eval Reward", self.eval_reward_placeholder)
			
		# logging
		self.merged = tf.summary.merge_all()
		self.file_writer = tf.summary.FileWriter(self.FLAGS.output_path, self.sess.graph)

	def add_loss_op(self):
		raise NotImplementedError()

	def add_optimizer_op(self):
		raise NotImplementedError()

class LinearQ(Network):

	def add_loss_op(self):
		#need implementation
		pass

	def add_optimizer_op(self, scope):
		#need implementation
		pass

	def get_q_values_op(self, state, scope, reuse=False):
		#need implementation
		pass

class FeedQ(Network):

	def add_loss_op(self):
		#need implementation
		pass

	def add_optimizer_op(self, scope):
		#need implementation
		pass

	def get_q_values_op(self, state, scope, reuse=False):
		#need implementation
		pass

class DeepQ(Network):

	def add_loss_op(self):
		self.q = self.get_q_values_op(self.proc_s, scope=self.scope, reuse=False)
		self.target_q = self.get_q_values_op(self.proc_sp, scope=self.target_scope, reuse=False)

		q_samp = self.r + self.FLAGS.gamma*(-tf.to_float(self.done_mask)+1.0)*tf.reduce_max(self.target_q,axis=1)
		q_s = tf.reduce_sum(self.q * tf.one_hot(self.a, self.num_actions), axis=1)

		losses = tf.square(q_samp-q_s)
		self.loss = tf.reduce_mean(losses)

	def add_optimizer_op(self):
		opt = tf.train.AdamOptimizer(self.lr)
		grads_and_vars = opt.compute_gradients(self.loss, var_list = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope = self.scope))
		clipped_grads_and_vars=[]
		clipped_grads_list=[]
		if (self.FLAGS.grad_clip):
			for grads,var in grads_and_vars:
				clipped_grads = tf.clip_by_norm(grads, self.FLAGS.clip_val)
				clipped_grads_and_vars.append((clipped_grads,var))
				clipped_grads_list.append(clipped_grads)

			self.train_op = opt.apply_gradients(clipped_grads_and_vars)
			self.grad_norm = tf.global_norm(clipped_grads_list)
		else:
			self.train_op = opt.apply_gradients(grads_and_vars)
			self.grad_norm = tf.global_norm([grads for grads, _ in grads_and_vars])

	def get_q_values_op(self, state, scope, reuse=False):
		with tf.variable_scope(scope):
			out = layers.conv2d(inputs=state, num_outputs = 32, kernel_size=[8,8], stride=[4,4], padding="SAME", activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"1")
			out = layers.conv2d(inputs=out, num_outputs = 64, kernel_size=[4,4], stride=[2,2], padding="SAME", activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"2")
			out = layers.conv2d(inputs=out, num_outputs = 64, kernel_size=[3,3], stride=[1,1], padding="SAME", activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"3")
			out = layers.flatten(out, scope=scope)
			out = layers.fully_connected(inputs=out, num_outputs = 512, activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"4")
			out = layers.fully_connected(inputs=out, num_outputs = self.num_actions, activation_fn = None, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"5")
		return out

class DeepAC(Network):
		
	def add_placeholders_op(self):
		self.s = tf.placeholder(tf.uint8, [None, self.img_height, self.img_width, self.img_depth*self.FLAGS.state_hist])
		self.a = tf.placeholder(tf.int32, [None])
		self.r = tf.placeholder(tf.float32, [None])
		self.criticBest = tf.placeholder(tf.float32, [None])
		self.actorDiff = tf.placeholder(tf.float32, [None])
		self.sp = tf.placeholder(tf.uint8, [None, self.img_height, self.img_width, self.img_depth*self.FLAGS.state_hist])
		self.done_mask = tf.placeholder(tf.bool, [None])
		self.lr = tf.placeholder(tf.float32, [])

	def add_loss_op(self):
		self.actor, self.critic = self.get_actor_critic_values(self.proc_s, scope=self.scope, reuse=False)
		self.criticLoss = tf.reduce_mean(tf.square(self.critic-self.criticBest))
		self.actorLoss = tf.reduce_mean(tf.square(self.actor[self.a]))

	def add_optimizer_op(self, scope):
		#need implementation
		pass

	def get_actor_critic_values(self, state, scope, reuse=False):
		with tf.variable_scope(scope):
			out = layers.conv2d(inputs=state, num_outputs = 32, kernel_size=[8,8], stride=[4,4], padding="SAME", activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"1")
			out = layers.conv2d(inputs=out, num_outputs = 64, kernel_size=[4,4], stride=[2,2], padding="SAME", activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"2")
			out = layers.conv2d(inputs=out, num_outputs = 64, kernel_size=[3,3], stride=[1,1], padding="SAME", activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"3")
			out = layers.flatten(out, scope=scope)
			out = layers.fully_connected(inputs=out, num_outputs = 512, activation_fn=tf.nn.relu, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"4")
			out1 = layers.fully_connected(inputs=out, num_outputs = self.num_actions, activation_fn = None, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"5")
			out2 = layers.fully_connected(inputs=out, num_outputs = 1, activation_fn = None, weights_initializer=layers.xavier_initializer(), biases_initializer=tf.constant_initializer(0), scope=scope+"6")
		return out1, out2


	def update_step(self, t, replay_buffer, lr):
		s_batch, a_batch, r_batch, sp_batch, done_mask_batch, criticBest_batch, actorDiff_batch = replay_buffer.sample(self.FLAGS.batch_size)

		fd = {
			# inputs
			self.s: s_batch,
			self.a: a_batch,
			self.r: r_batch,
			self.sp: sp_batch, 
			self.done_mask: done_mask_batch,
			self.lr: lr,
			self.criticBest: criticBest_batch,
			self.actorDiff: actorDiff_batch,
			# extra info
			self.avg_reward_placeholder: self.avg_reward, 
			self.max_reward_placeholder: self.max_reward, 
			self.std_reward_placeholder: self.std_reward, 
			self.avg_q_placeholder: self.avg_q, 
			self.max_q_placeholder: self.max_q, 
			self.std_q_placeholder: self.std_q, 
			self.eval_reward_placeholder: self.eval_reward, 
		}

		output_list = [self.loss, self.grad_norm, self.merged, self.train_op]
		loss_eval, grad_norm_eval, summary, _ = self.sess.run(output_list, feed_dict=fd)

		# tensorboard stuff
		self.file_writer.add_summary(summary, t)
		
		return loss_eval, grad_norm_eval