import tensorflow as tf
import numpy as np
import logging
import gflags
from needle.helper.fisher_vector_product import FisherVectorProduct
from needle.helper.utils import declare_variables, select

FLAGS = gflags.FLAGS


class Net(FisherVectorProduct):
    def __init__(self, state_dim, action_dim):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = FLAGS.learning_rate
        self.scope = "actor"

    @declare_variables
    def build_infer(self):
        self.op_inputs = tf.placeholder(tf.float32, [None, None, self.state_dim])

        self.batch_size = tf.shape(self.op_inputs)[0]
        # logging.info(self.op_inputs[:, 0, :].get_shape())

        h = tf.contrib.layers.fully_connected(
            inputs=self.op_inputs,
            num_outputs=FLAGS.num_units,
            # biases_initializer=None,
            activation_fn=tf.nn.relu,
        )
        self.op_logits = tf.contrib.layers.fully_connected(
            inputs=h,
            num_outputs=self.action_dim,
            # biases_initializer=None,
            activation_fn=None,
        )
        self.op_actions = tf.nn.softmax(self.op_logits)

    def build_train(self):

        self.op_advantages = tf.placeholder(tf.float32)
        self.op_choices = tf.placeholder(tf.int32, [None, None])
        self.op_mask = tf.placeholder(tf.float32)
        self.op_length = tf.placeholder(tf.float32)
        self.op_old_logits = tf.placeholder(tf.float32)

        # op_actions_log_prob = -tf.nn.sparse_softmax_cross_entropy_with_logits(self.op_logits, self.op_choices)
        # self.op_loss = tf.reduce_sum(-self.op_advantages * op_actions_log_prob * self.op_mask) / \
        #                tf.to_float(self.batch_size)
        self.op_loss = tf.reduce_sum(
            -self.op_advantages * self.op_mask *
            tf.exp(select(tf.nn.log_softmax(self.op_logits) - tf.nn.log_softmax(self.op_old_logits), self.op_choices))
        ) / tf.to_float(self.batch_size)

        self.op_grad = self.flatten_gradient(self.op_loss)

        # TRUE KL divergence should be the following. However, constants are ignored
        # self.kl_divergence = self.old_distribution * tf.log(self.old_distribution / tf.nn.softmax(self.logits))

        self.op_kl_divergence = tf.reduce_sum(
            # tf.nn.softmax_cross_entropy_with_logits(self.op_old_logits, self.op_actions) * self.op_mask,
            tf.stop_gradient(tf.nn.softmax(self.op_old_logits) * tf.expand_dims(self.op_mask, 2)) *
                (tf.nn.log_softmax(self.op_old_logits) - tf.nn.log_softmax(self.op_logits))
        ) / tf.reduce_sum(self.op_length)

        # Hessian-vector product
        self.build_fisher_vector_product(self.op_kl_divergence)

    def get_dict(self, lengths, mask, inputs, choices, advantages, old_logits):
        return {
            self.op_mask: mask,
            self.op_inputs: inputs,
            self.op_length: lengths,
            self.op_choices: choices,
            self.op_advantages: advantages,
            self.op_old_logits: old_logits,
        }

    def fisher_vector_product(self, vec, feed_dict):
        return self._infer_fisher_vector_product(vec, feed_dict)

    def infer(self, inputs):
        logits = tf.get_default_session().run(
            self.op_logits,
            feed_dict={
                self.op_inputs: inputs,
            }
        )
        return logits

    def gradient(self, feed_dict):
        return self.get_flat_gradient(
            self.op_grad,
            feed_dict=feed_dict,
        )

    def reset(self):
        pass

    def test(self, feed_dict):
        return tf.get_default_session().run(
            [self.op_loss, self.op_kl_divergence],
            feed_dict=feed_dict,
        )

