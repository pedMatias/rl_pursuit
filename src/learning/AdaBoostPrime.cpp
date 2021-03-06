/*
File: AdaBoostPrime.cpp
Author: Samuel Barrett
Description: AdaBoost' from David Pardoe's thesis: AdaBoost that doesn't change the source data weights
Created:  2012-01-20
Modified: 2012-01-20
*/

#include "AdaBoostPrime.h"
  
AdaBoostPrime::AdaBoostPrime(const std::vector<Feature> &features, bool caching, SubClassifierGenerator baseLearner, const Json::Value &baseLearnerOptions, unsigned int maxBoostingIterations):
  AdaBoost(features,caching,baseLearner,baseLearnerOptions,maxBoostingIterations),
  onlySourceData(true)
{
  name = "AdaBoostPrime";
}

void AdaBoostPrime::addData(const InstancePtr &instance) {
  onlySourceData = false;
  AdaBoost::addData(instance);
}

void AdaBoostPrime::addSourceData(const InstancePtr &instance) {
  assert(onlySourceData);
  AdaBoost::addData(instance);
  endSourceData = data.size();
  reweightStartInd = data.size();
}
