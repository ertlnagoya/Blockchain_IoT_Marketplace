<script lang="ts">
  import PurchaseButton from './purchaseButton.svelte';
  export let data: {
    datasetCID?: string;
    provider?: string;
    item?: { cid?: string; owner?: string };
  } = {};
  
  const datasetCID = data.datasetCID ?? data.item?.cid ?? '';
  const providerAddress = data.provider ?? data.item?.owner ?? '';
</script>

<PurchaseButton {datasetCID} {providerAddress} />