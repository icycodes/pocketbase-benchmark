<script>
    /** @type {import('./$types').PageData} */
    export let data;
</script>

<h1>Hello PocketBase</h1>
<p id="is-valid">Auth Store is valid: {data.isValid}</p>
{#if data.isValid}
    <p id="user-email">User Email: {data.model?.email}</p>
    <p id="token">Token: {data.token}</p>
{:else}
    <p id="not-logged-in">Not logged in.</p>
{/if}
