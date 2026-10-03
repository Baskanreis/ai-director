from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class ResourceBudget: gpu_memory_mb:int=4096; model_memory_mb:int=2048; max_concurrent_models:int=2; max_batch_size:int=8
@dataclass(frozen=True)
class ResourceDecision: batch_size:int; concurrent_models:int; quality:str; reason:str
class ResourceManager:
 def __init__(self,budget=None): self.budget=budget or ResourceBudget()
 def plan(self,requested_batch=8,requested_models=2,quality='final',estimated_model_mb=1024):
  free=max(256,self.budget.gpu_memory_mb-self.budget.model_memory_mb); per=max(128,estimated_model_mb); capacity=max(1,free//per); concurrency=max(1,min(requested_models,self.budget.max_concurrent_models,capacity)); batch=max(1,min(requested_batch,self.budget.max_batch_size,max(1,(free//max(256,per))*4))); q=quality
  if free<per*2 and quality=='final': q='balanced'
  if free<per: q='fast'
  return ResourceDecision(batch,concurrency,q,f'gpu_budget={self.budget.gpu_memory_mb}MB estimated_model={estimated_model_mb}MB')
